# 上传 GitHub

## 网页上传

1. 解压 `digital-communication-lab-github.zip` 到一个文件夹。
2. 在 GitHub 创建名为 `digital-communication-lab` 的空仓库。
3. 使用仓库中的上传文件入口，上传解压后的全部项目文件和子文件夹。
4. README.md、core.py、main.py 等文件应直接位于仓库根目录，避免多套一层文件夹。
5. 检查 `.gitignore` 等隐藏文件是否一并上传，填写提交说明并完成提交。

不要仅把 ZIP 本身上传为仓库源码；GitHub 需要展开的文件来展示 README、代码和图片。

## Git 命令上传

前提：已安装 Git，在 GitHub 创建了空仓库，并将下面的 YOUR_USERNAME 换成实际用户名。

在解压后的项目根目录打开终端，执行：

```bash
git init
git add .
git commit -m "Add digital communication simulation project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/digital-communication-lab.git
git push -u origin main
```

首次提交如果提示缺少身份，先配置你自己的 Git 用户名和邮箱。首次推送按提示登录。以上命令适用于尚未初始化 Git 的文件夹和空远程仓库。

## 发布前自查

- README 首页图片能显示，运行命令可执行。
- `python verify.py` 验证通过。
- 不上传虚拟环境、IDE 配置、缓存、账号令牌或密码。
- 当前包附带 MIT 许可证，允许在保留许可证声明的条件下使用、修改和分发。
- 可将仓库简介填写为：Python 数字通信基带仿真：BPSK/QPSK/16QAM、AWGN、误码率分析与自适应调制可视化。
