# The viewer: mouse wheel and touchpad page turning, ↑ ↓ keys, Ctrl + wheel and pinch zoom, in the real program.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from helpers import App, FIX, Report, display

r = Report()
check = r.check
HELPERS = '''() => {
  window.__wheel = (o) => {
    const r = document.querySelector('#stage').getBoundingClientRect();
    const ev = new WheelEvent('wheel', Object.assign({ bubbles: true, cancelable: true,
      clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 }, o));
    document.querySelector('#pageCanvas').dispatchEvent(ev);
    return ev.defaultPrevented;
  };
  // a touchpad: a stream of small steps, one per frame
  window.__swipe = async (dy, n) => { for (let i = 0; i < n; i++) { __wheel({ deltaY: dy }); await new Promise(r => setTimeout(r, 16)); } };
  window.__label = () => parseInt(document.querySelector('#zoomLabel').textContent, 10);
  window.__st = () => { const s = document.querySelector('#stage'); return { top: Math.round(s.scrollTop), max: s.scrollHeight - s.clientHeight }; };
  window.__ink = () => { const c = document.querySelector('#pageCanvas');
    const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0;
    for (let i = 0; i < d.length; i += 4 * 7) if (d[i + 3] > 0 && d[i] < 160) n++; return n; };
}'''
DOWN = '__wheel({ deltaY: 100, wheelDeltaY: -120 })'      # one mouse wheel notch, as Chromium reports it
UP = '__wheel({ deltaY: -100, wheelDeltaY: 120 })'
ZIN = '__wheel({ deltaY: -100, wheelDeltaY: 120, ctrlKey: true })'
ZOUT = '__wheel({ deltaY: 100, wheelDeltaY: -120, ctrlKey: true })'


with display(), sync_playwright() as p:
    app = App('viewer')
    app.start(FIX / 'doc1.pdf')
    try:
        b, pg = app.page(p)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.wait_for_function('state.pdfDoc && document.querySelector("#pageCanvas").width > 0', timeout=30000)
        pg.wait_for_timeout(400)
        pg.evaluate(HELPERS)
        cur = lambda: pg.evaluate('state.currentPage')
        ev = lambda js: pg.evaluate(js)
        n = ev('state.numPages')

        # ---- fit page (the default): the whole page is visible, so the wheel turns pages
        check('fit_page_has_nothing_to_scroll', ev('__st().max') <= 1, ev('__st()'))
        pv = ev(DOWN); check('notch_down_turns', cur() == 2 and pv, [cur(), pv])
        ev(UP); check('notch_up_turns_back', cur() == 1, cur())
        ev('async () => { for (let i = 0; i < 3; i++) { %s; await new Promise(r => setTimeout(r, 25)); } }' % DOWN)
        check('fast_notches_turn_a_page_each', cur() == 4, cur())
        pg.wait_for_timeout(300)
        ev('__swipe(6, 45)'); check('touchpad_swipe_turns_once', cur() == 5, cur())
        pg.wait_for_timeout(300)
        ev('__swipe(6, 45)'); check('next_swipe_turns_again', cur() == 6, cur())
        pg.wait_for_timeout(300)
        ev('__swipe(-6, 45)'); check('swipe_up_turns_back', cur() == 5, cur())
        pg.wait_for_timeout(300)
        ev('__swipe(3, 5)'); check('light_touch_does_not_turn', cur() == 5, cur())
        pg.wait_for_timeout(300)

        # ---- the first and the last page: nothing to turn to
        ev('renderMainPage(1)'); pg.wait_for_timeout(300)
        ev(UP); check('no_page_before_the_first', cur() == 1, cur())
        ev('renderMainPage(%d)' % n); pg.wait_for_timeout(300)
        ev(DOWN); check('no_page_after_the_last', cur() == n, cur())
        pg.wait_for_timeout(300)

        # ---- fit width: the page is taller than the view, so it scrolls first and turns at its edge
        ev('renderMainPage(3)'); pg.click('#zoomFit'); pg.wait_for_timeout(600)
        st = ev('__st()'); check('fit_width_is_taller_than_the_view', st['max'] > 100, st)
        pv = ev(DOWN); check('wheel_scrolls_inside_the_page', cur() == 3 and not pv, [cur(), pv])
        ev('document.querySelector("#stage").scrollTop = 1e6'); pg.wait_for_timeout(100)
        ev(DOWN); pg.wait_for_timeout(400)
        check('at_the_bottom_the_wheel_turns', cur() == 4 and ev('__st().top') == 0, [cur(), ev('__st()')])
        ev(UP); pg.wait_for_timeout(400)
        st = ev('__st()')
        check('at_the_top_it_turns_back_to_the_bottom', cur() == 3 and st['top'] >= st['max'] - 2, [cur(), st])

        # ---- ↑ ↓ keys: scroll the page, turn at its edge
        ev('document.querySelector("#stage").scrollTop = 0'); pg.wait_for_timeout(100)
        pg.keyboard.press('ArrowDown'); pg.wait_for_timeout(400)
        check('arrow_down_scrolls', cur() == 3 and ev('__st().top') > 0, [cur(), ev('__st()')])
        ev('document.querySelector("#stage").scrollTop = 1e6'); pg.wait_for_timeout(100)
        pg.keyboard.press('ArrowDown'); pg.wait_for_timeout(400)
        check('arrow_down_at_the_bottom_turns', cur() == 4, cur())
        pg.keyboard.press('ArrowUp'); pg.wait_for_timeout(400)
        check('arrow_up_at_the_top_turns_back', cur() == 3, cur())
        pg.fill('#pageNumInput', '5'); pg.keyboard.press('ArrowDown'); pg.wait_for_timeout(200)
        check('arrows_in_the_page_box_are_left_alone', cur() == 3, cur())
        pg.keyboard.press('Enter'); pg.wait_for_timeout(400)
        check('page_box_goes_to_the_page', cur() == 5, cur())

        # ---- zoom: Ctrl + wheel and pinch, around the cursor, 400% at most
        pg.click('#zoomPage'); pg.wait_for_timeout(500)
        z0 = ev('__label()')
        ev(ZIN); pg.wait_for_timeout(400)
        z1 = ev('__label()')
        check('ctrl_wheel_zooms_in_one_step', abs(z1 / z0 - 1.2) < 0.03 and cur() == 5, [z0, z1, cur()])
        ev(ZOUT); pg.wait_for_timeout(400)
        check('ctrl_wheel_zooms_out', abs(ev('__label()') - z0) <= 1, [z0, ev('__label()')])
        ev('__wheel({ deltaY: -10, ctrlKey: true })'); pg.wait_for_timeout(400)
        check('pinch_follows_the_fingers', abs(ev('__label()') / z0 - 2.718281828 ** 0.1) < 0.03, [z0, ev('__label()')])
        ev('__wheel({ deltaY: -1000, wheelDeltaY: 1200, ctrlKey: true })'); pg.wait_for_timeout(400)
        check('big_wheel_step_is_one_notch', ev('__label()') <= z0 * 1.11 * 1.21, ev('__label()'))
        for _ in range(30):
            ev(ZIN)
        pg.wait_for_timeout(800)
        check('zoom_stops_at_400', ev('__label()') == 400, ev('__label()'))
        check('zoomed_page_is_drawn', ev('__ink()') > 100 and ev('document.querySelector("#pageCanvas").width') > 2000, [ev('__ink()'), ev('document.querySelector("#pageCanvas").width')])
        pg.click('#zoomOut'); pg.wait_for_timeout(500)
        check('minus_button', abs(ev('__label()') - 400 / 1.2) <= 1, ev('__label()'))
        pg.click('#zoomPage')
        try:                                         # a 400% page takes a moment to draw again on a slow PC
            pg.wait_for_function('Math.abs(__label() - %d) <= 1' % z0, timeout=10000)
        except Exception:
            pass
        check('fit_page_again', abs(ev('__label()') - z0) <= 1, [z0, ev('__label()')])

        # ---- 文字识别 (picking pages) turns pages the same way
        c0 = cur()
        ev('setMode("ocr")'); pg.wait_for_timeout(500)
        ev(DOWN); pg.wait_for_timeout(300); ev(DOWN); pg.wait_for_timeout(300)
        check('turns_pages_on_ocr_screen_too', cur() == c0 + 2, [c0, cur()])
        check('no_page_errors', not errs, errs)
        b.close()
    finally:
        app.stop()
r.finish()
