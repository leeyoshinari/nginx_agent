# nginx_agent
It can only be used with [MyPlatform](https://github.com/leeyoshinari/MyPlatform.git), and can't be used alone.

## Deploy
1. Clone Repository
    ```shell script
    git clone https://github.com/leeyoshinari/nginx_agent.git
    ```

2. Modify `config.conf`. Usually don't need to modify, unless you have special requirements.
    If the path of `access.log` isn't found automatically, the path need to be set in `config.conf` manually.

3. Modify Nginx log format in `nginx.conf`. <br>
    Custom log format is
    ```
    log_format  main   '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent $upstream_response_time "$http_referer" "$http_user_agent" "$http_x_forwarded_for"';
   ```
   Use custom log format 
   ```
   access_log  logs/access.log  main;
   ``` 
   
   If you want to output other information, please add it to end of log format.

4. Package. Using `pyinstaller` to package python code. 
- (1) Enter folder, run:<br>
    ```shell
    pyinstaller -F server.py -p dealController.py -p common.py -p __init__.py --hidden-import dealController --hidden-import common
    ```
- (2) Copy `config.conf` to the `dist` folder, cmd: `cp config.conf dist/`
- (3) Enter `dist` folder, zip files, cmd: `zip nginx_agent.zip server config.conf`
- (4) Upload zip file to [MyPlatform](https://github.com/leeyoshinari/MyPlatform.git)
- (5) Deploy nginx_agent
   
NOTE: For Linux Server, the executable file packaged on the server of the CentOS system X86 architecture can only run on the server of the CentOS system X86 architecture; servers of other system and architecture need to be repackaged. <br>
