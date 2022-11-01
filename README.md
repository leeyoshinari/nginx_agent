# nginx_agent


## Deploy

nginx 配置文件中的日志自定义格式设置需要修改成：
`log_format  main   '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent $upstream_response_time "$http_referer" "$http_user_agent" "$http_x_forwarded_for"';`
并且取消注释，启用自定义日志格式
`access_log  logs/access.log  main;`

如果你还需要一些其他的信息也输出到日志中，请在日志末尾增加，否则需要修改正则表达式。


## Package
Using `pyinstaller` to package python code. After packaging, it can be quickly deployed on other Servers without installing python3.7+ and third-party packages.<br>
Before packaging, you must ensure that the python code can run normally.<br>
- (1) Enter folder, run:<br>
    ```shell
    pyinstaller -F server.py -p dealController.py -p common.py -p __init__.py --hidden-import dealController --hidden-import common
    ```
- (2) Copy `config.conf` to the `dist` folder, cmd: `cp config.conf dist/`
- (3) Enter `dist` folder, zip files, cmd: `zip nginx_agent.zip server config.conf`
- (4) Upload zip file to [MyPlatform](https://github.com/leeyoshinari/MyPlatform.git)
- (5) Deploy nginx_agent
   
   NOTE: Since it runs on the server to be monitored, the executable file packaged on the server of the CentOS system X86 architecture can only run on the server of the CentOS system X86 architecture; servers of other system and architecture need to be repackaged. <br>

