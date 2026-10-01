import Cocoa
import WebKit
// 用法：swift tools_snap.swift <html> <png> <宽度> [js]
let a = CommandLine.arguments
let url = URL(fileURLWithPath: a[1]); let out = a[2]; let width = CGFloat(Double(a[3])!)
let js = a.count > 4 ? a[4] : ""
class D: NSObject, WKNavigationDelegate {
  let wv: WKWebView
  init(_ w: WKWebView) { wv = w }
  func webView(_ w: WKWebView, didFinish n: WKNavigation!) {
    w.evaluateJavaScript(js + ";document.documentElement.scrollHeight") { r, _ in
      DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
        w.evaluateJavaScript("document.documentElement.scrollHeight") { r, _ in
          let h = CGFloat((r as? NSNumber)?.doubleValue ?? 2000)
          w.frame = NSRect(x: 0, y: 0, width: width, height: h)
          DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            let c = WKSnapshotConfiguration(); c.rect = NSRect(x: 0, y: 0, width: width, height: h)
            w.takeSnapshot(with: c) { img, e in
              guard let img = img, let t = img.tiffRepresentation, let b = NSBitmapImageRep(data: t),
                    let p = b.representation(using: .png, properties: [:]) else { print("失败", e as Any); exit(1) }
              try! p.write(to: URL(fileURLWithPath: out)); print("输出", out, Int(width), Int(h)); exit(0)
            }
          }
        }
      }
    }
  }
}
let app = NSApplication.shared
let wv = WKWebView(frame: NSRect(x: 0, y: 0, width: width, height: 1200))
let win = NSWindow(contentRect: wv.frame, styleMask: [.borderless], backing: .buffered, defer: false)
win.contentView = wv
let d = D(wv); wv.navigationDelegate = d
wv.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
app.run()
