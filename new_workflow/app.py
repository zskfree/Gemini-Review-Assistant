from flask import Flask, render_template, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename
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
from src.task_manager import task_manager

app = Flask(__name__)

# 获取配置中的路径
PDF_FOLDER = get_config("paths.pdf_folder")
TOPIC_FILE = get_config("paths.research_topic_file")
REF_FILE = get_config("paths.reference_file")
RESULT_CSV = get_config("paths.result_csv", "new_workflow/txts_zsk/summary_sorted.csv")
# 尝试查找配置文件，与 config_loader 逻辑保持一致或直接指定
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.yaml")

# 全局单例 task_manager 已导入

@app.route('/events')
def events():
    return Response(task_manager.listen(), mimetype='text/event-stream')

@app.route('/get-progress')
def get_progress():
    return jsonify(task_manager.get_progress())

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
def save_config_route():
    """保存前端修改后的配置"""
    try:
        new_config = request.json
        from src.config_loader import save_config
        save_config(CONFIG_FILE, new_config)
        
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
    
    
    # 防止路径遍历
    safe_filename = secure_filename(filename)
    # 额外检查：确保解析后的绝对路径仍在 PDF_FOLDER 内
    requested_path = os.path.abspath(os.path.join(PDF_FOLDER, filename))
    trusted_path = os.path.abspath(PDF_FOLDER)
    
    if not requested_path.startswith(trusted_path):
        logger.warning(f"Security Alert: Path traversal attempt detected: {filename}")
        return jsonify({"status": "error", "message": "非法的文件名"})

    # 优先使用 request 中的 filename 进行查找 (如果它不含非法字符)，或者限制只能删除当前目录文件
    # 这里我们强制只能删除 PDF_FOLDER 下的文件
    if not os.path.exists(requested_path):
        return jsonify({"status": "error", "message": "文件不存在"})

    try:
        os.remove(requested_path)
        logger.info(f"Deleted PDF file: {filename}")
        return jsonify({"status": "success", "message": f"已删除 {filename}"})
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
                safe_name = secure_filename(file.filename)
                file.save(os.path.join(PDF_FOLDER, safe_name))
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
            task_manager.update_progress(0, 0, "正在保存配置...")
            with open(TOPIC_FILE, 'w', encoding='utf-8', newline='') as f:
                f.write(research_topic)
            with open(REF_FILE, 'w', encoding='utf-8', newline='') as f:
                f.write(reference_list)

            task_manager.update_progress(0, 1, "正在分析文献映射关系 (这可能需要几分钟)...")
            logger.info("Starting literature mapping...")
            
            mapping, error = get_mapping_step()
            
            if error:
                logger.warning(f"Mapping step returned error: {error}")
                task_manager.announce_error('mapping_result', error)
                task_manager.update_progress(0, 0, f"映射失败: {error}")
            else:
                logger.info("Literature mapping completed successfully")
                task_manager.update_progress(1, 1, "映射完成")
                task_manager.announce_event('mapping_result', {"status": "success", "mapping": mapping})

        except Exception as e:
            logger.error(f"Error in background mapping: {e}", exc_info=True)
            task_manager.announce_error('mapping_result', str(e))

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
            # 执行总结步骤，传入进度回调
            success, message, stats = run_summary_step(progress_callback=task_manager.update_progress)
            
            if success:
                logger.info(f"Summary generation completed: {message}")
                result_data = {
                    "status": "success",
                    "message": message,
                    "stats": stats,
                    "download_url": "/download"
                }
                task_manager.announce_event('summary_result', result_data)
                task_manager.update_progress(100, 100, "所有任务已完成")
            else:
                logger.warning(f"Summary generation failed: {message}")
                task_manager.announce_error('summary_result', message)
                
        except Exception as e:
            logger.error(f"Error in background summary: {e}", exc_info=True)
            task_manager.announce_error('summary_result', str(e))

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
    