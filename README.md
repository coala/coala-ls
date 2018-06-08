# coala-ls

A coala language server based on [Language Server Protocol (LSP)](https://github.com/Microsoft/language-server-protocol/blob/master/protocol.md). Python versions 3.x is supported.


## Setting up your dev environment, coding, and debugging

You'll need python version 3.5 or greater, run `pip3 install -r requirements.txt` to install the requirements, and run `python3 -m coalals --mode=tcp --addr=2087` to start a local languager server listening at port 2087.

Then you should update the `./vscode-client/src/extension.ts` to make client in TCP mode.

```diff
export function activate(context: ExtensionContext) {
-   context.subscriptions.push(startLangServer
-   (require("path").resolve(__dirname, '../coala-langserver.sh'), ["python"]));
+   context.subscriptions.push(startLangServerTCP(2087, ["python"]));
    console.log("coala language server is running.");
}
```

To try it in [Visual Studio Code](https://code.visualstudio.com), open ./vscode-client in VS Code and turn to debug view, launch the extension.

## Reference

* [python-langserver](https://github.com/sourcegraph/python-langserver)
* [python-language-server](http://github.com/palantir/python-language-server)
