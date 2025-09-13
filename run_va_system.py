
import os
import sys
import time
import signal
import subprocess
import logging
from pathlib import Path
from threading import Thread

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VASystemLauncher:
    """VA系统启动器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.server_dir = self.project_root / "va-framework" / "server"
        self.client_dir = self.project_root / "client"
        
        self.server_process = None
        self.client_process = None
        self.running = False
    
    def check_dependencies(self):
        """检查依赖"""
        logger.info("检查系统依赖...")
        
        # 检查Python环境
        python_version = sys.version_info
        
        # 检查Node.js环境（可选）
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Node.js版本: {result.stdout.strip()}")
            else:
                logger.warning("未检测到Node.js环境，前端需要手动启动")
        except FileNotFoundError:
            logger.warning("未检测到Node.js环境，前端需要手动启动")
        
        logger.info("✓ 依赖检查完成")
    
    def install_python_dependencies(self):
        """安装Python依赖"""
        requirements_file = self.server_dir / "requirements.txt"
        
        if not requirements_file.exists():
            logger.warning("未找到requirements.txt文件")
            return
        
        logger.info("安装Python依赖包...")
        try:
            cmd = [sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)]
            result = subprocess.run(cmd, cwd=self.server_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✓ Python依赖安装完成")
            else:
                logger.error(f"Python依赖安装失败: {result.stderr}")
                
        except Exception as e:
            logger.error(f"安装Python依赖失败: {e}")
    
    def install_node_dependencies(self):
        """安装Node.js依赖"""
        package_json = self.client_dir / "package.json"
        
        if not package_json.exists():
            logger.warning("未找到package.json文件")
            return
        
        logger.info("安装Node.js依赖包...")
        try:
            # 尝试使用pnpm，如果没有则使用npm
            pnpm_cmd = ['pnpm', 'install']
            npm_cmd = ['npm', 'install']
            
            try:
                result = subprocess.run(pnpm_cmd, cwd=self.client_dir, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("✓ Node.js依赖安装完成 (pnpm)")
                    return
            except FileNotFoundError:
                pass
            
            result = subprocess.run(npm_cmd, cwd=self.client_dir, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✓ Node.js依赖安装完成 (npm)")
            else:
                logger.error(f"Node.js依赖安装失败: {result.stderr}")
                
        except Exception as e:
            logger.error(f"安装Node.js依赖失败: {e}")
    
    def start_server(self):
        """启动后端服务器"""
        logger.info("启动后端服务器...")
        
        run_script = self.server_dir / "run.py"
        if not run_script.exists():
            logger.error("未找到后端启动脚本")
            return False
        
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.server_dir)
            
            self.server_process = subprocess.Popen(
                [sys.executable, str(run_script)],
                cwd=self.server_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 等待服务器启动
            time.sleep(3)
            
            if self.server_process.poll() is None:
                logger.info("✓ 后端服务器启动成功 (PID: %d)", self.server_process.pid)
                logger.info("  后端地址: http://localhost:5000")
                return True
            else:
                logger.error("后端服务器启动失败")
                return False
                
        except Exception as e:
            logger.error(f"启动后端服务器失败: {e}")
            return False
    
    def start_client(self):
        """启动前端开发服务器"""
        logger.info("启动前端开发服务器...")
        
        package_json = self.client_dir / "package.json"
        if not package_json.exists():
            logger.warning("未找到package.json，跳过前端启动")
            return False
        
        try:
            # 尝试使用pnpm dev，如果没有则使用npm run dev
            pnpm_cmd = ['pnpm', 'run', 'dev']
            npm_cmd = ['npm', 'run', 'dev']
            
            try:
                self.client_process = subprocess.Popen(
                    pnpm_cmd,
                    cwd=self.client_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            except FileNotFoundError:
                self.client_process = subprocess.Popen(
                    npm_cmd,
                    cwd=self.client_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            # 等待前端服务器启动
            time.sleep(5)
            
            if self.client_process.poll() is None:
                logger.info("✓ 前端开发服务器启动成功 (PID: %d)", self.client_process.pid)
                logger.info("  前端地址: http://localhost:3333")
                return True
            else:
                logger.error("前端开发服务器启动失败")
                return False
                
        except Exception as e:
            logger.error(f"启动前端开发服务器失败: {e}")
            return False
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info("收到停止信号，正在关闭服务...")
        self.stop()
        sys.exit(0)
    
    def stop(self):
        """停止所有服务"""
        self.running = False
        
        if self.server_process:
            logger.info("停止后端服务器...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
        
        if self.client_process:
            logger.info("停止前端开发服务器...")
            self.client_process.terminate()
            try:
                self.client_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.client_process.kill()
        
        logger.info("✓ 所有服务已停止")
    
    def run(self, install_deps=True, start_client=True):
        """运行系统"""
        print("=" * 80)
        print("🚀 工商投诉数据分析系统 (基于va-framework)")
        print("=" * 80)
        
        try:
            # 注册信号处理器
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # 检查依赖
            self.check_dependencies()
            
            # 安装依赖
            if install_deps:
                self.install_python_dependencies()
                if start_client:
                    self.install_node_dependencies()
            
            # 启动后端
            if not self.start_server():
                logger.error("后端启动失败，退出")
                return False
            
            # 启动前端
            if start_client:
                if not self.start_client():
                    logger.warning("前端启动失败，仅运行后端服务")
            
            self.running = True
            
            print("-" * 80)
            print("🎉 系统启动完成！")
            print()
            print("📍 访问地址:")
            print("   后端API: http://localhost:5000")
            if start_client:
                print("   前端界面: http://localhost:3333")
            print()
            print("💡 使用说明:")
            print("   - 后端API文档: http://localhost:5000/")
            print("   - 健康检查: http://localhost:5000/health")
            print("   - 按 Ctrl+C 停止系统")
            print("-" * 80)
            
            # 保持运行
            while self.running:
                time.sleep(1)
                
                # 检查进程状态
                if self.server_process and self.server_process.poll() is not None:
                    logger.error("后端服务器意外停止")
                    break
                    
                if start_client and self.client_process and self.client_process.poll() is not None:
                    logger.warning("前端开发服务器意外停止")
            
        except KeyboardInterrupt:
            logger.info("用户中断，正在停止...")
        except Exception as e:
            logger.error(f"系统运行出错: {e}")
        finally:
            self.stop()
        
        return True

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='工商投诉数据分析系统启动器')
    parser.add_argument('--no-install', action='store_true', help='跳过依赖安装')
    parser.add_argument('--server-only', action='store_true', help='仅启动后端服务')
    parser.add_argument('--client-only', action='store_true', help='仅启动前端服务')
    
    args = parser.parse_args()
    
    launcher = VASystemLauncher()
    
    if args.client_only:
        logger.info("仅启动前端模式")
        launcher.start_client()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            launcher.stop()
    else:
        success = launcher.run(
            install_deps=not args.no_install,
            start_client=not args.server_only
        )
        
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

