# MMTautofeed-Build
将`MMTautofeed.py`打包成`.app`和`.exe`，供MMT发布组发种使用
配合下面的生成器，填写`程序最终名称 (App Name)`、`主程序文件名 (Python File)`、`自定义图标 (可选 Icon)`、`依赖包列表 (Dependencies)`、，输出`yaml`
[⚙️ MMT 自动化打包配置生成器](https://yaml-generator.pages.dev/)
回填至`.github`里面的`yaml`文件中
通过`actions`分别打包
