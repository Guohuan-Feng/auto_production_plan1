FROM crxchinacdhprod.azurecr.cn/python:3.12
  
# 设置工作目录  
WORKDIR /app  
  
# 复制依赖文件并安装依赖  
COPY requirements.txt .  
RUN pip install --upgrade pip \
 && pip install --no-cache -r requirements.txt
  
# 复制应用代码  
COPY . ./
  
# 启动命令，使用 uvicorn 运行 FastAPI 应用  
CMD ["bash"]