from flask import Flask, render_template, request, jsonify, send_file, Response
import os
import yaml
import shutil
import threading
import queue
import json
import time
from workflow import run_workflow, get_mapping_step, run_summary_step
from src.config_loader import get_config
from src.pdf_processor import get_pdf_files
from src.logger import logger

app = Flask(__name__)

# 获取配置中的路径
PDF_FOLDER = get_config("paths.pdf_folder")
TOPIC_FILE = get_config("paths.research_topic_file")
REF_FILE = get_config("paths.reference_file")
RESULT_CSV = "new_workflow/txts_zsk/summary_sorted.csv"
CONFIG_FILE = "new_workflow/config.yaml"

# SSE 消息广播器
class MessageAnnouncer:
    def __init__(self):
        self.listeners = []
        self.lock = threading.Lock()

    def listen(self):
        q = queue.Queue(maxsize=10)
        with self.lock:
            self.listeners.append(q)
        return q

    def announce(self, msg):
        with self.lock:
            for i in reversed(range(len(self.listeners))):
                try:
                    self.listeners[i].put_nowait(msg)
                except queue.Full:
                    del self.listeners[i]

announcer = MessageAnnouncer()

def format_sse(data: str, event=None) -> str:
    msg = f"data: {data}\n\n"
    if event:
        msg = f"event: {event}\n{msg}"
    return msg

# 全局进度状态 (保留用于 fallback)
PROGRESS = {
    "current": 0,
    "total": 0,
    "last_item": "等待中..."
}

# 确保目录存在
os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(TOPIC_FILE), exist_ok=True)

def update_progress_state(current, total, last_item):
    global PROGRESS
    PROGRESS["current"] = current
    PROGRESS["total"] = total
    PROGRESS["last_item"] = last_item
    # 同时通过 SSE 广播
    data = json.dumps({'current': current, 'total': total, 'message': last_item})
    announcer.announce(format_sse(data, event='progress'))
    logger.debug(f"Progress Update: {current}/{total} - {last_item}")

@app.route('/events')
def events():
    def stream():
        messages = announcer.listen()
        while True:
            msg = messages.get()
            yield msg
    return Response(stream(), mimetype='text/event-stream')

@app.route('/get-progress')
def get_progress():
    return jsonify(PROGRESS)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/get-data', methods=['GET'])
def get_data():
    """获取当前配置文件夹中的内容及配置参数"""
    try:
        # 读取研究主题
        topic = ""
        if os.path.exists(TOPIC_FILE):
            with open(TOPIC_FILE, 'r', encoding='utf-8', newline='') as f:
                topic = f.read()
        
        # 读取参考文献列表
        refs = ""
        if os.path.exists(REF_FILE):
            with open(REF_FILE, 'r', encoding='utf-8', newline='') as f:
                refs = f.read()
        
        # 获取已有的 PDF 文件列表
        pdf_files = []
        if os.path.exists(PDF_FOLDER):
            pdf_files = get_pdf_files(PDF_FOLDER)
            
        # 读取配置文件
        config_data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
        return jsonify({
            "status": "success",
            "research_topic": topic,
            "reference_list": refs,
            "existing_pdfs": pdf_files,
            "config": config_data # 返回配置信息
        })
    except Exception as e:
        logger.error(f"Error in get_data: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)})

@app.route('/save-config', methods=['POST'])
def save_config():
    """保存前端修改后的配置"""
    try:
        new_config = request.json
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(new_config, f, allow_unicode=True, sort_keys=False)
        logger.info("Configuration updated via Web UI")
        return jsonify({"status": "success", "message": "配置已更新"})
    except Exception as e:
        logger.error(f"Error saving config: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)})

@app.route('/delete-pdf', methods=['POST'])
def delete_pdf():
    """删除指定的 PDF 文件"""
    filename = request.json.get('filename')
    if not filename:
        return jsonify({"status": "error", "message": "未指定文件名"})
    
    file_path = os.path.join(PDF_FOLDER, filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted PDF file: {filename}")
            return jsonify({"status": "success", "message": f"已删除 {filename}"})
        return jsonify({"status": "error", "message": "文件不存在"})
    except Exception as e:
        logger.error(f"Error deleting PDF {filename}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)})

@app.route('/upload-pdfs', methods=['POST'])
def upload_pdfs():
    """独立上传 PDF 文件的接口"""
    try:
        files = request.files.getlist('pdfs')
        saved_count = 0
        for file in files:
            if file and file.filename.endswith('.pdf'):
                # 确保文件名安全并保存
                file.save(os.path.join(PDF_FOLDER, file.filename))
                saved_count += 1
        
        logger.info(f"Uploaded {saved_count} PDF files")
        return jsonify({
            "status": "success", 
            "message": f"成功上传 {saved_count} 个文件",
            "existing_pdfs": [f for f in os.listdir(PDF_FOLDER) if f.endswith('.pdf')]
        })
    except Exception as e:
        logger.error(f"Error uploading PDFs: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)})

@app.route('/run-mapping', methods=['POST'])
def run_mapping_api():
    # 1. 预处理请求数据
    research_topic = request.form.get('research_topic', '').replace('\r\n', '\n')
    reference_list = request.form.get('reference_list', '').replace('\r\n', '\n')
    
    # 2. 定义后台任务
    def background_task():
        try:
            update_progress_state(0, 0, "正在保存配置...")
            with open(TOPIC_FILE, 'w', encoding='utf-8', newline='') as f:
                f.write(research_topic)
            with open(REF_FILE, 'w', encoding='utf-8', newline='') as f:
                f.write(reference_list)

            update_progress_state(0, 1, "正在分析文献映射关系 (这可能需要几分钟)...")
            logger.info("Starting literature mapping...")
            
            mapping, error = get_mapping_step()
            
            if error:
                logger.warning(f"Mapping step returned error: {error}")
                error_data = json.dumps({"status": "error", "message": error})
                announcer.announce(format_sse(error_data, event='mapping_result'))
                update_progress_state(0, 0, f"映射失败: {error}")
            else:
                logger.info("Literature mapping completed successfully")
                update_progress_state(1, 1, "映射完成")
                success_data = json.dumps({"status": "success", "mapping": mapping})
                announcer.announce(format_sse(success_data, event='mapping_result'))

        except Exception as e:
            logger.error(f"Error in background mapping: {e}", exc_info=True)
            error_data = json.dumps({"status": "error", "message": str(e)})
            announcer.announce(format_sse(error_data, event='mapping_result'))

    # 3. 启动线程并立即响应
    thread = threading.Thread(target=background_task)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started", "message": "Backend processing started"})

@app.route('/run-summary', methods=['POST'])
def run_summary_api():
    
    def background_task():
        try:
            logger.info("Starting summary generation...")
            # 执行总结步骤，传入进度回调 (update_progress_state 已经会自动 SSE 广播)
            success, message, stats = run_summary_step(progress_callback=update_progress_state)
            
            if success:
                logger.info(f"Summary generation completed: {message}")
                result_data = json.dumps({
                    "status": "success",
                    "message": message,
                    "stats": stats,
                    "download_url": "/download"
                })
                announcer.announce(format_sse(result_data, event='summary_result'))
                update_progress_state(100, 100, "所有任务已完成")
            else:
                logger.warning(f"Summary generation failed: {message}")
                error_data = json.dumps({"status": "error", "message": message})
                announcer.announce(format_sse(error_data, event='summary_result'))
                
        except Exception as e:
            logger.error(f"Error in background summary: {e}", exc_info=True)
            error_data = json.dumps({"status": "error", "message": str(e)})
            announcer.announce(format_sse(error_data, event='summary_result'))

    thread = threading.Thread(target=background_task)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started", "message": "Backend processing started"})


@app.route('/run-workflow', methods=['POST'])
def run_workflow_api():
    try:
        # 1. 处理研究主题和参考文献列表
        research_topic = request.form.get('research_topic', '').replace('\r\n', '\n')
        reference_list = request.form.get('reference_list', '').replace('\r\n', '\n')
        
        with open(TOPIC_FILE, 'w', encoding='utf-8', newline='') as f:
            f.write(research_topic)
        
        with open(REF_FILE, 'w', encoding='utf-8', newline='') as f:
            f.write(reference_list)

        # 2. 处理上传的 PDF 文件 (保留此逻辑以兼容直接点击处理的情况)
        files = request.files.getlist('pdfs')
        saved_count = 0
        for file in files:
            if file and file.filename.endswith('.pdf'):
                file.save(os.path.join(PDF_FOLDER, file.filename))
                saved_count += 1

        if not os.listdir(PDF_FOLDER):
            return jsonify({"status": "error", "message": "目录中没有 PDF 文件，请先上传。"})

        # 3. 执行工作流
        logger.info("Executing full workflow via API...")
        run_workflow()

        if os.path.exists(RESULT_CSV):
            logger.info("Workflow execution completed successfully")
            return jsonify({
                "status": "success", 
                "message": f"处理完成！共处理 {saved_count} 个新文件。",
                "download_url": "/download"
            })
        else:
            logger.error("Workflow finished but result CSV is missing")
            return jsonify({"status": "error", "message": "处理完成但未生成结果文件，请检查日志。"})

    except Exception as e:
        logger.error(f"Error in run_workflow_api: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)})

@app.route('/download')
def download_result():
    if os.path.exists(RESULT_CSV):
        return send_file(
            os.path.abspath(RESULT_CSV),
            as_attachment=True,
            download_name="文献综述结果.csv"
        )
    return "文件不存在", 404

if __name__ == '__main__':
    logger.info("Starting ScholarFlow Flask server on port 18690...")
    app.run(debug=False, port=18690)
    