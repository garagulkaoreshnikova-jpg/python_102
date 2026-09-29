import AppKit
import CoreGraphics

@MainActor
final class SpanielView: NSView {
    var frames: [NSImage] = []
    var frameIndex = 0
    var facesRight = true

    override func draw(_ dirtyRect: NSRect) {
        guard !frames.isEmpty else { return }
        let image = frames[frameIndex % frames.count]
        let target = bounds.insetBy(dx: 3, dy: 3)

        NSGraphicsContext.saveGraphicsState()
        if !facesRight {
            let flip = NSAffineTransform()
            flip.translateX(by: bounds.width, yBy: 0)
            flip.scaleX(by: -1, yBy: 1)
            flip.concat()
        }
        image.draw(in: target, from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil)
        NSGraphicsContext.restoreGraphicsState()
    }
}

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    private var statusItem: NSStatusItem!
    private var pauseItem: NSMenuItem!
    private var window: NSWindow!
    private var spanielView: SpanielView!
    private var animationTimer: Timer?
    private var paused = false
    private var walkStartedAt: TimeInterval = 0
    private var startX: CGFloat = 0
    private var endX: CGFloat = 0
    private var direction: CGFloat = 1
    private var baseY: CGFloat = 0
    private let companionSize = NSSize(width: 232, height: 220)

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        makeStatusMenu()
        makeCompanionWindow()
        scheduleWalk(after: 9)
    }

    private func makeStatusMenu() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        if let button = statusItem.button {
            button.image = NSImage(systemSymbolName: "pawprint.fill", accessibilityDescription: "Кавалер")
            button.toolTip = "Кавалер Кинг Чарльз спаниель"
        }

        let menu = NSMenu()
        menu.delegate = self
        let walkItem = NSMenuItem(title: "Пройтись сейчас", action: #selector(walkNow), keyEquivalent: "")
        walkItem.target = self
        menu.addItem(walkItem)
        pauseItem = NSMenuItem(title: "Поставить на паузу", action: #selector(togglePause), keyEquivalent: "")
        pauseItem.target = self
        menu.addItem(pauseItem)
        menu.addItem(.separator())
        let quitItem = NSMenuItem(title: "Завершить", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)
        statusItem.menu = menu
    }

    func menuWillOpen(_ menu: NSMenu) {
        pauseItem.title = paused ? "Продолжить прогулки" : "Поставить на паузу"
    }

    private func makeCompanionWindow() {
        let screen = NSScreen.main ?? NSScreen.screens.first!
        let visible = screen.visibleFrame
        let frame = NSRect(x: visible.minX - companionSize.width,
                           y: visible.minY + 14,
                           width: companionSize.width,
                           height: companionSize.height)

        window = NSWindow(contentRect: frame,
                          styleMask: .borderless,
                          backing: .buffered,
                          defer: false)
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = false
        window.level = .floating
        window.ignoresMouseEvents = true
        window.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary]

        spanielView = SpanielView(frame: NSRect(origin: .zero, size: companionSize))
        spanielView.frames = loadFrames()
        window.contentView = spanielView
        window.orderOut(nil)
    }

    private func loadFrames() -> [NSImage] {
        guard let sheetURL = Bundle.main.url(forResource: "spaniel-sheet", withExtension: "png"),
              let sheet = NSImage(contentsOf: sheetURL) else {
            return []
        }
        var proposed = NSRect(origin: .zero, size: sheet.size)
        guard let cgImage = sheet.cgImage(forProposedRect: &proposed, context: nil, hints: nil) else {
            return []
        }

        let frameWidth = cgImage.width / 2
        let frameHeight = cgImage.height / 2
        var images: [NSImage] = []
        for row in 0..<2 {
            for column in 0..<2 {
                let crop = CGRect(x: column * frameWidth,
                                  y: row * frameHeight,
                                  width: frameWidth,
                                  height: frameHeight)
                if let frame = cgImage.cropping(to: crop) {
                    images.append(NSImage(cgImage: frame,
                                          size: NSSize(width: frameWidth, height: frameHeight)))
                }
            }
        }
        return images
    }

    private func scheduleWalk(after delay: TimeInterval? = nil) {
        guard !paused else { return }
        let interval = delay ?? TimeInterval.random(in: 35...90)
        DispatchQueue.main.asyncAfter(deadline: .now() + interval) { [weak self] in
            guard let self, !self.paused else { return }
            self.beginWalk()
        }
    }

    private func beginWalk() {
        guard !paused, !spanielView.frames.isEmpty else { return }
        let screen = NSScreen.main ?? NSScreen.screens.first!
        let visible = screen.visibleFrame
        direction = Bool.random() ? 1 : -1
        startX = direction > 0 ? visible.minX - companionSize.width : visible.maxX
        endX = direction > 0 ? visible.maxX : visible.minX - companionSize.width
        baseY = visible.minY + 12
        walkStartedAt = ProcessInfo.processInfo.systemUptime

        spanielView.facesRight = direction > 0
        spanielView.frameIndex = 0
        window.setFrameOrigin(NSPoint(x: startX, y: baseY))
        window.orderFrontRegardless()

        animationTimer?.invalidate()
        animationTimer = Timer.scheduledTimer(withTimeInterval: 1.0 / 30.0, repeats: true) { [weak self] timer in
            guard let self else { timer.invalidate(); return }
            self.updateWalk()
        }
    }

    private func updateWalk() {
        let elapsed = ProcessInfo.processInfo.systemUptime - walkStartedAt
        let distance = abs(endX - startX)
        let duration = max(1, distance / 118)
        let progress = min(elapsed / duration, 1)
        let x = startX + (endX - startX) * progress
        let bounce = sin(elapsed * 11) * 2.5

        window.setFrameOrigin(NSPoint(x: x, y: baseY + bounce))
        spanielView.frameIndex = Int(elapsed * 7) % max(spanielView.frames.count, 1)
        spanielView.needsDisplay = true

        if progress >= 1 {
            animationTimer?.invalidate()
            animationTimer = nil
            window.orderOut(nil)
            scheduleWalk()
        }
    }

    @objc private func walkNow() {
        animationTimer?.invalidate()
        beginWalk()
    }

    @objc private func togglePause() {
        paused.toggle()
        if paused {
            animationTimer?.invalidate()
            animationTimer = nil
            window.orderOut(nil)
        } else {
            scheduleWalk(after: 2)
        }
    }

    @objc private func quit() {
        NSApp.terminate(nil)
    }
}

@main
@MainActor
enum CavalierCompanionApp {
    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.run()
    }
}
