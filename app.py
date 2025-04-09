import os
import sys
import json
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory # type: ignore

# 确保 src 目录在 Python 路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")  # 添加 src 目录
sys.path.insert(0, src_dir)  # 确保 src 目录在路径中

from src import config_loader, file_finder, reference_parser, llm_api, summarizer, final_generator

app = Flask(__name__)

# 全局变量存储处理状态
processing_status = {
    "is_processing": False,
    "current_step": "",
    "progress": 0,
    "total": 0,
    "message": "",
    "summaries": [],
    "final_draft": ""
}

def reset_status():
    """重置处理状态"""
    global processing_status
    processing_status = {
        "is_processing": False,
        "current_step": "",
        "progress": 0,
        "total": 0,
        "message": "",
        "summaries": [],
        "final_draft": ""
    }

@app.route('/')
def index():
    """渲染主页"""
    # 加载配置
    try:
        config = config_loader.load_config("config.yaml")
        prompts = config_loader.load_all_prompts(config)
    except Exception as e:
        return render_template('index.html', error=f"配置加载失败: {e}")
    
    # 扫描PDF文件
    pdf_dir = config['paths']['pdf_dir']
    all_pdf_files = file_finder.find_pdf_files(pdf_dir)
    
    # 获取参考文献映射
    ref_list_path = os.path.join(config['paths']['txt_dir'], config['prompts']['references_list_file'])
    pdf_to_ref_map, missing_refs, missing_pdfs = reference_parser.parse_references(ref_list_path, all_pdf_files)
    
    # 准备文件列表数据
    pdf_files_data = []
    for pdf_path in all_pdf_files:
        filename = os.path.basename(pdf_path)
        has_ref = pdf_path in pdf_to_ref_map
        ref_text = pdf_to_ref_map.get(pdf_path, "缺少引用信息")
        pdf_files_data.append({
            "path": pdf_path,
            "filename": filename,
            "has_ref": has_ref,
            "ref_text": ref_text
        })
    
    return render_template(
        'index.html', 
        pdf_files=pdf_files_data,
        research_theme=prompts.get('research_theme', '未设置研究主题'),
        config=config
    )

def process_pdfs_background(selected_pdfs, config):
    """后台处理PDF总结的线程函数"""
    global processing_status
    
    processing_status["is_processing"] = True
    processing_status["current_step"] = "加载配置"
    
    try:
        # 加载配置
        prompts = config_loader.load_all_prompts(config)
        api_key = config.get('llm', {}).get('api_key') or os.getenv("GEMINI_API_KEY")
        if not api_key or not all([prompts.get('research_theme'), prompts.get('summary_prompt')]):
            processing_status["message"] = "配置文件或环境变量缺失必要信息"
            processing_status["is_processing"] = False
            return
        
        # 解析引用
        processing_status["current_step"] = "解析引用"
        pdf_dir = config['paths']['pdf_dir']
        all_pdf_files = file_finder.find_pdf_files(pdf_dir)
        
        ref_list_path = os.path.join(config['paths']['txt_dir'], config['prompts']['references_list_file'])
        pdf_to_ref_map, _, _ = reference_parser.parse_references(ref_list_path, all_pdf_files)
        
        # 文献总结
        processing_status["current_step"] = "处理PDF总结"
        processing_status["total"] = len(selected_pdfs)
        processing_status["progress"] = 0
        
        # 修改进度回调函数的实现
        def progress_callback(current, total, message=""):
            """进度回调函数，确保进度不超过总数"""
            global processing_status
            processing_status["progress"] = min(current + 1, total)  # 添加边界检查
            processing_status["total"] = total
            if message:
                processing_status["message"] = message
            print(f"Progress update: {min(current+1, total)}/{total} - {message}")  # 调试输出
        
        # 使用summarizer处理文献总结
        all_summaries = summarizer.process_all_pdfs(
            pdfs_to_process=selected_pdfs,
            ref_map=pdf_to_ref_map,
            research_theme=prompts['research_theme'],
            summary_prompt_template=prompts['summary_prompt'],
            llm_api_func=llm_api.call_llm_with_pdf,
            api_key=api_key,
            model_name=config['llm'].get('model_name', 'gemini-2.0-flash'),
            cache_path=config['paths']['cache_file'],
            cache_enabled=config.get('cache', {}).get('enabled', True),
            timeout=config['llm'].get('request_timeout', 300),
            progress_callback=progress_callback,  # 传入回调函数
            **{k: v for k, v in config['llm'].items() if k not in ['model_name', 'api_key', 'request_timeout']}
        )
        
        # 保存总结结果
        summary_output_path = config['paths']['summary_output_file']
        os.makedirs(os.path.dirname(summary_output_path), exist_ok=True)
        with open(summary_output_path, 'w', encoding='utf-8') as f:
            json.dump(all_summaries, f, ensure_ascii=False, indent=4)
            
        processing_status["summaries"] = all_summaries
        processing_status["current_step"] = "总结完成"
        processing_status["message"] = f"成功处理 {len([s for s in all_summaries if s.get('status') == 'Success'])} 篇文献"
    
    except Exception as e:
        processing_status["message"] = f"处理过程中出错: {str(e)}"
    
    finally:
        # 确保进度不超过总数
        if processing_status["progress"] > processing_status["total"] and processing_status["total"] > 0:
            processing_status["progress"] = processing_status["total"]
        processing_status["is_processing"] = False


def generate_final_background(output_type, config):
    """后台生成最终文稿的线程函数"""
    global processing_status
    
    processing_status["is_processing"] = True
    processing_status["current_step"] = "生成最终文稿"
    processing_status["message"] = "正在调用模型生成最终文稿，这可能需要几分钟..."
    
    try:
        # 加载配置
        prompts = config_loader.load_all_prompts(config)
        api_key = config.get('llm', {}).get('api_key') or os.getenv("GEMINI_API_KEY")
        
        # 获取选择的提示词模板
        final_prompt_key = 'review_final_prompt' if output_type == 'review' else 'qualitative_final_prompt'
        final_prompt_template = prompts.get(final_prompt_key)
        
        if not final_prompt_template:
            processing_status["message"] = f"未找到类型 '{output_type}' 对应的最终生成提示词"
            processing_status["is_processing"] = False
            return
        
        # 从现有的总结中获取成功的部分
        successful_summaries = [s for s in processing_status["summaries"] if s.get('status') == 'Success']
        
        # 如果没有成功的总结，尝试从文件中加载
        if not successful_summaries:
            try:
                summary_output_path = config['paths']['summary_output_file']
                if os.path.exists(summary_output_path):
                    with open(summary_output_path, 'r', encoding='utf-8') as f:
                        all_summaries = json.load(f)
                        successful_summaries = [s for s in all_summaries if s.get('status') == 'Success']
                        if successful_summaries:
                            processing_status["summaries"] = all_summaries
            except Exception as load_err:
                processing_status["message"] = f"无法加载之前的总结结果: {str(load_err)}"
                processing_status["is_processing"] = False
                return
        
        # 再次检查是否有成功的总结
        if not successful_summaries:
            processing_status["message"] = "没有成功的文献总结可用于生成最终文稿"
            processing_status["is_processing"] = False
            return
        
        # 生成最终文稿
        final_draft, error_msg = final_generator.generate_final_draft(
            successful_summaries=successful_summaries,
            research_theme=prompts['research_theme'],
            final_prompt_template=final_prompt_template,
            llm_api_func_text=llm_api.call_llm_text_only,
            model_name=config['llm'].get('final_draft_model_name', config['llm'].get('model_name')),
            api_key=api_key,
            output_file=config['paths']['final_output_file'],
            timeout=config['llm'].get('request_timeout', 600),
            temperature=config['llm'].get('temperature', 1.2),
            max_retries=config['llm'].get('max_retries', 3)
        )
        
        if final_draft:
            processing_status["final_draft"] = final_draft
            processing_status["current_step"] = "生成完成"
            processing_status["message"] = f"最终文稿生成完成，长度: {len(final_draft)} 字符"
        else:
            processing_status["message"] = f"最终文稿生成失败: {error_msg}"
    
    except Exception as e:
        processing_status["message"] = f"生成过程中出错: {str(e)}"
    
    finally:
        processing_status["is_processing"] = False


@app.route('/api/process-pdfs', methods=['POST'])
def process_pdfs():
    """处理选定的PDF文件"""
    selected_pdfs = request.json.get('selected_pdfs', [])
    if not selected_pdfs:
        return jsonify({"error": "未选择任何PDF文件"}), 400
    
    # 重置状态
    reset_status()
    
    # 加载配置
    try:
        config = config_loader.load_config("config.yaml")
    except Exception as e:
        return jsonify({"error": f"配置加载失败: {e}"}), 500
    
    # 启动后台线程处理
    thread = threading.Thread(target=process_pdfs_background, args=(selected_pdfs, config))
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "开始处理PDF文件"})


@app.route('/api/generate-final', methods=['POST'])
def generate_final():
    """生成最终文稿"""
    output_type = request.json.get('output_type', 'review')
    
    # 加载配置
    try:
        config = config_loader.load_config("config.yaml")
    except Exception as e:
        return jsonify({"error": f"配置加载失败: {e}"}), 500
    
    # 启动后台线程生成
    thread = threading.Thread(target=generate_final_background, args=(output_type, config))
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": f"开始生成{output_type}类型文稿"})


@app.route('/api/status')
def get_status():
    """获取当前处理状态"""
    return jsonify(processing_status)


@app.route('/download/<path:filename>')
def download_file(filename):
    """下载生成的文件"""
    directory = os.path.dirname(filename)
    file = os.path.basename(filename)
    return send_from_directory(directory, file, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)