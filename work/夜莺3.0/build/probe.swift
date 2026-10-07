import Cocoa
import WebKit
// 用 WebKit 打开本地页面，等待若干秒后执行一段 JS 并打印结果（无头检查用）。
// 用法：swiftc -O -o probe build/probe.swift && ./probe <html> <等待秒数> <js表达式>
let a = CommandLine.arguments
let url = URL(fileURLWithPath: a[1]); let wait = Double(a[2])!; let js = a[3]
class D: NSObject, WKNavigationDelegate {
  func webView(_ w: WKWebView, didFinish n: WKNavigation!) {
    DispatchQueue.main.asyncAfter(deadline: .now() + wait) {
      w.evaluateJavaScript(js) { r, e in print(r ?? "nil", e ?? ""); exit(0) }
    }
  }
}
let app = NSApplication.shared
let wv = WKWebView(frame: NSRect(x: 0, y: 0, width: 1400, height: 900))
let win = NSWindow(contentRect: wv.frame, styleMask: [.borderless], backing: .buffered, defer: false)
win.contentView = wv
let d = D(); wv.navigationDelegate = d
wv.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
app.run()
