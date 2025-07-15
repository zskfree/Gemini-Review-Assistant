from flask import Flask, render_template, request, jsonify, send_from_directory # type: ignore
import os
import sys
import threading
import time
import webbrowser
import argparse
import json
import yaml

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

# 添加自动打开浏览器的函数
def open_browser(host, port, delay=1.0):
    """在指定延迟后打开浏览器"""
    def _open_browser():
        time.sleep(delay)  # 延迟一段时间确保Flask服务器已启动
        url = f'http://{host}:{port}/'
        print(f"正在打开浏览器访问: {url}")
        webbrowser.open(url)

    threading.Thread(target=_open_browser).start()

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

@app.route('/config')
def config_page():
    """配置页面"""
    try:
        config = config_loader.load_config("config.yaml")
        prompts = config_loader.load_all_prompts(config)
        return render_template('config.html', config=config, prompts=prompts)
    except Exception as e:
        return render_template('config.html', error=f"配置加载失败: {e}")

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取当前配置"""
    try:
        config = config_loader.load_config("config.yaml")
        prompts = config_loader.load_all_prompts(config)
        return jsonify({
            "config": config,
            "prompts": prompts
        })
    except Exception as e:
        return jsonify({"error": f"配置加载失败: {e}"}), 500

@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        data = request.json
        config_data = data.get('config')
        prompts_data = data.get('prompts')
        
        # 更新配置文件
        if config_data:
            with open('config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        
        # 更新提示词文件
        if prompts_data:
            config = config_loader.load_config("config.yaml")
            txt_dir = config['paths']['txt_dir']
            
            for key, content in prompts_data.items():
                if key in config['prompts']:
                    filename = config['prompts'][key]
                    file_path = os.path.join(txt_dir, filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
        
        return jsonify({"message": "配置更新成功"})
    except Exception as e:
        return jsonify({"error": f"配置更新失败: {e}"}), 500

@app.route('/api/config/test', methods=['POST'])
def test_config():
    """测试配置"""
    try:
        test_type = request.json.get('type')
        
        if test_type == 'api':
            # 直接使用llm_api的文本调用功能测试
            config = config_loader.load_config("config.yaml")
            model_name = config.get('llm', {}).get('model_name', 'gemini-2.5-flash')
            
            # 尝试一个简单的API调用
            result, error = llm_api.call_llm_text_only(
                model_name=model_name,
                prompt_text="请回复：测试成功",
                api_key=None,  # 使用全局配置
                max_retries=1,
                temperature=0.1
            )
            
            if result and "测试成功" in result:
                return jsonify({"success": True, "message": "API连接测试成功！"})
            else:
                return jsonify({"success": False, "message": f"API测试失败: {error or '返回结果异常'}"})
        
        return jsonify({"success": False, "message": "未知的测试类型"})
    except Exception as e:
        return jsonify({"success": False, "message": f"测试失败: {str(e)}"})

@app.route('/reference-check')
def reference_check_page():
    """参考文献核对页面"""
    try:
        config = config_loader.load_config("config.yaml")
        return render_template('reference_check.html', config=config)
    except Exception as e:
        return render_template('reference_check.html', error=f"配置加载失败: {e}")

@app.route('/api/reference-check', methods=['GET'])
def check_references():
    """检查参考文献与PDF文件的匹配情况"""
    try:
        config = config_loader.load_config("config.yaml")
        
        # 扫描PDF文件
        pdf_dir = config['paths']['pdf_dir']
        all_pdf_files = file_finder.find_pdf_files(pdf_dir)
        
        # 获取参考文献映射
        ref_list_path = os.path.join(config['paths']['txt_dir'], config['prompts']['references_list_file'])
        pdf_to_ref_map, missing_refs, missing_pdfs = reference_parser.parse_references(ref_list_path, all_pdf_files)
        
        # 准备返回数据
        pdf_files_info = []
        for pdf_path in all_pdf_files:
            filename = os.path.basename(pdf_path)
            filename_without_ext = os.path.splitext(filename)[0]
            has_ref = pdf_path in pdf_to_ref_map
            ref_text = pdf_to_ref_map.get(pdf_path, "")
            
            pdf_files_info.append({
                "path": pdf_path,
                "filename": filename,
                "filename_without_ext": filename_without_ext,
                "has_ref": has_ref,
                "ref_text": ref_text
            })
        
        # 加载参考文献列表
        ref_entries = []
        if os.path.exists(ref_list_path):
            with open(ref_list_path, 'r', encoding='utf-8') as f:
                ref_entries = [line.strip() for line in f if line.strip()]
        
        return jsonify({
            "pdf_files": pdf_files_info,
            "ref_entries": ref_entries,
            "missing_refs": missing_refs,
            "missing_pdfs": missing_pdfs,
            "matched_count": len(pdf_to_ref_map),
            "total_pdf_count": len(all_pdf_files),
            "total_ref_count": len(ref_entries)
        })
        
    except Exception as e:
        return jsonify({"error": f"检查失败: {str(e)}"}), 500

@app.route('/api/rename-file', methods=['POST'])
def rename_file():
    """重命名PDF文件"""
    try:
        data = request.json
        old_path = data.get('old_path')
        new_filename = data.get('new_filename')
        
        if not old_path or not new_filename:
            return jsonify({"error": "缺少必要参数"}), 400
        
        # 确保新文件名有.pdf扩展名
        if not new_filename.lower().endswith('.pdf'):
            new_filename += '.pdf'
        
        # 构建新路径
        directory = os.path.dirname(old_path)
        new_path = os.path.join(directory, new_filename)
        
        # 检查新文件是否已存在
        if os.path.exists(new_path) and old_path != new_path:
            return jsonify({"error": "目标文件名已存在"}), 400
        
        # 重命名文件
        os.rename(old_path, new_path)
        
        return jsonify({
            "message": "文件重命名成功",
            "new_path": new_path,
            "new_filename": new_filename
        })
        
    except Exception as e:
        return jsonify({"error": f"重命名失败: {str(e)}"}), 500


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
        # 不要传递api_key参数，让llm_api使用全局客户端列表
        if not all([prompts.get('research_theme'), prompts.get('summary_prompt')]):
            processing_status["message"] = "配置文件缺失必要信息"
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
            api_key=None,  # 不传递api_key，使用全局客户端列表
            model_name=config['llm'].get('model_name', 'gemini-2.5-flash'),
            cache_path=config['paths']['cache_file'],
            cache_enabled=config.get('cache', {}).get('enabled', True),
            progress_callback=progress_callback,  # 传入回调函数
            # 只传递PDF处理函数需要的参数，排除final_draft_model_name
            **{k: v for k, v in config['llm'].items() 
               if k not in ['model_name', 'api_key', 'request_timeout', 'final_draft_model_name']}
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
        # 不要直接从配置获取api_key，使用None让系统使用全局客户端
        # api_key = config.get('llm', {}).get('api_key') or os.getenv("GEMINI_API_KEY")
        
        # 获取选择的提示词模板
        final_prompt_key = 'review_final_prompt' if output_type == 'review' else 'qualitative_final_prompt'
        final_prompt_template = prompts.get(final_prompt_key)
        
        if not final_prompt_template:
            processing_status["message"] = f"未找到类型 '{output_type}' 对应的最终生成提示词"
            processing_status["current_step"] = "生成失败"
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
                processing_status["current_step"] = "生成失败"
                processing_status["is_processing"] = False
                return

        # 再次检查是否有成功的总结
        if not successful_summaries:
            processing_status["message"] = "没有成功的文献总结可用于生成最终文稿"
            processing_status["current_step"] = "生成失败"
            processing_status["is_processing"] = False
            return

        # 根据输出类型设置不同的输出文件路径
        base_output_file = config['paths']['final_output_file']
        if output_type == 'qualitative':
            # 为定性研究论文使用不同的文件名
            output_file = base_output_file.replace('最终结果.txt', '定性研究论文.txt')
        else:
            output_file = base_output_file
        
        # 生成最终文稿 - 使用None让系统使用全局客户端轮换
        print("正在准备生成最终文稿...")
        final_draft, error_msg = final_generator.generate_final_draft(
            successful_summaries=successful_summaries,
            research_theme=prompts['research_theme'],
            final_prompt_template=final_prompt_template,
            llm_api_func_text=llm_api.call_llm_text_only,
            model_name=config['llm'].get('final_draft_model_name', 'gemini-2.5-flash'),
            api_key=None,  # 修改这里：使用None而不是从配置获取
            output_file=output_file,
            temperature=config['llm'].get('temperature', 1.2),
            max_retries=config['llm'].get('max_retries', 3)
        )
        
        if final_draft:
            processing_status["final_draft"] = final_draft
            processing_status["output_file"] = output_file  # 添加输出文件路径
            processing_status["current_step"] = "生成完成"
            processing_status["message"] = f"最终文稿生成完成，长度: {len(final_draft)} 字符"
        else:
            processing_status["current_step"] = "生成失败"
            processing_status["message"] = f"最终文稿生成失败: {error_msg}"
    
    except Exception as e:
        processing_status["current_step"] = "生成失败"
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
    try:
        # 如果是相对路径，使用当前工作目录
        if not os.path.isabs(filename):
            filepath = os.path.join(os.getcwd(), filename)
        else:
            filepath = filename
            
        directory = os.path.dirname(filepath)
        file = os.path.basename(filepath)
        
        # 检查文件是否存在
        if not os.path.exists(filepath):
            return jsonify({"error": "文件不存在"}), 404
            
        return send_from_directory(directory, file, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"下载失败: {str(e)}"}), 500


if __name__ == '__main__':
    # 添加命令行参数解析
    parser = argparse.ArgumentParser(description='Gemini文献综述助手')
    parser.add_argument('--no-browser', action='store_true', 
                        help='启动时不自动打开浏览器')
    parser.add_argument('--port', type=int, default=5000,
                        help='Web服务器端口（默认：5000）')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='Web服务器主机（默认：127.0.0.1）')
    args = parser.parse_args()
    
    # 如果没有指定--no-browser参数，启动浏览器
    if not args.no_browser and not os.environ.get("WERKZEUG_RUN_MAIN"):
        open_browser(args.host, args.port)
    app.run(debug=True, host=args.host, port=args.port)