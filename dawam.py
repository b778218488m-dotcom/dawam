# -*- coding: utf-8 -*-
"""فكرة للطباعة الرقمية - نظام تسجيل الدوام"""
import sys, os, json, re, uuid, hashlib
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QUrl, QMarginsF
from PySide6.QtGui import (QPalette, QColor, QPainter, QFont, QTextDocument, QPageSize, QPageLayout,
                           QPdfWriter, QDesktopServices, QTextOption)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QScrollArea, QComboBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QInputDialog, QMessageBox, QButtonGroup, QAbstractItemView)

OFFICE = "فكرة للطباعة الرقمية"
WIN = [(540, 720), (960, 1290)]          # 9-12 ، 4-9:30
SCH, DAYS = 510, 26                       # دقائق الدوام اليومي ، أيام الشهر للحساب
MONTHS = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']
APPDATA = Path(os.environ.get('APPDATA', Path.home())) / 'FekraDawam'
DOCS = Path.home() / 'Documents' / 'سجل الدوام'
DATA = APPDATA / 'data.json'

S = {'emps': [], 'logs': {}, 'pin': ''}
def load():
    global S
    try: S = json.loads(DATA.read_text(encoding='utf-8'))
    except Exception: pass
def save():
    APPDATA.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(S, ensure_ascii=False), encoding='utf-8')

# ---------- الحسابات ----------
def hm(ms):
    d = datetime.fromtimestamp(ms / 1000); return d.hour * 60 + d.minute
def tm(ms):
    d = datetime.fromtimestamp(ms / 1000); h = d.hour % 12 or 12
    return f"{h}:{d.minute:02d} {'ص' if d.hour < 12 else 'م'}"
def fm(m):
    m = round(abs(m)); return f"{m // 60}س {m % 60:02d}د"
def money(n): return f"{n:,.2f}"
def mlabel(m): return f"{MONTHS[int(m[5:]) - 1]} {m[:4]}"
def key_today(): return datetime.now().strftime('%Y-%m-%d')

def calc(ss, key):
    now = datetime.now(); today = key == key_today(); nm = now.hour * 60 + now.minute
    iv = []
    for s in ss:
        a = hm(s['i']); b = nm if s['o'] is None else hm(s['o']); iv.append((a, max(a, b)))
    tot = sum(b - a for a, b in iv)
    if datetime.strptime(key, '%Y-%m-%d').weekday() == 4:      # الجمعة إجازة
        return dict(tot=tot, over=tot, short=0, fri=True)
    cov = sh = 0
    for s, e in WIN:
        c = sum(max(0, min(b, e) - max(a, s)) for a, b in iv); cov += c
        eff = max(0, min(e, nm) - s) if today else e - s
        sh += max(0, eff - c)
    return dict(tot=tot, over=tot - cov, short=sh, fri=False)

def stats(e, m):
    L = S['logs'].get(e['id'], {}); to = ts = tw = 0; days = []
    for k in sorted(k for k in L if k.startswith(m)):
        c = calc(L[k], k); to += c['over']; ts += c['short']; tw += c['tot']
        days.append((k, c, L[k][0], L[k][-1]))
    due = max(0, e['salary'] + (to - ts) * e['salary'] / (DAYS * SCH))
    return dict(days=days, to=to, ts=ts, tw=tw, due=due)

def open_session(eid):
    for s in S['logs'].get(eid, {}).get(key_today(), []):
        if s['o'] is None: return s

# ---------- PDF ----------
def to_pdf(html, rel):
    f = DOCS / rel; f.parent.mkdir(parents=True, exist_ok=True)
    doc = QTextDocument(); opt = QTextOption(); opt.setTextDirection(Qt.RightToLeft); doc.setDefaultTextOption(opt)
    doc.setDefaultFont(QFont('Tahoma', 10)); doc.setHtml(html)
    w = QPdfWriter(str(f)); w.setPageSize(QPageSize(QPageSize.A4))
    w.setPageMargins(QMarginsF(14, 14, 14, 14), QPageLayout.Millimeter)
    doc.print_(w); return f

def page(body):
    return f"""<html dir="rtl"><body style="font-family:Tahoma">
<table width="100%" cellpadding="10" cellspacing="0"><tr><td bgcolor="#232c4e"><font color="#ffffff" size="5"><b>{OFFICE}</b></font></td></tr></table>
<table width="100%" cellspacing="0"><tr><td bgcolor="#00aeef" height="5"></td><td bgcolor="#ec008c"></td><td bgcolor="#ffd400"></td></tr></table><br>{body}</body></html>"""
def th(*c): return '<tr>' + ''.join(f'<th bgcolor="#232c4e"><font color="#ffffff">{x}</font></th>' for x in c) + '</tr>'
def td(*c): return '<tr>' + ''.join(f'<td align="center">{x}</td>' for x in c) + '</tr>'
def table(rows): return '<table width="100%" border="1" cellspacing="0" cellpadding="6">' + ''.join(rows) + '</table>'
def h(t): return f'<h3 align="center" style="color:#232c4e">{t}</h3>'

def month_table(m, mo):
    rows = [th('الموظف', *(['الراتب'] if mo else []), 'إجمالي الساعات', 'الإضافي', 'التأخير', *(['المستحق'] if mo else []))]
    for e in S['emps']:
        s = stats(e, m)
        rows.append(td(e['name'], *([money(e['salary'])] if mo else []), fm(s['tw']), fm(s['to']), fm(s['ts']), *([money(s['due'])] if mo else [])))
    return table(rows)
def year_html(y):
    b = h(f'تقرير الدوام السنوي — {y}')
    for i in range(1, 13):
        m = f'{y}-{i:02d}'
        if any(stats(e, m)['days'] for e in S['emps']): b += f'<h4>{mlabel(m)}</h4>' + month_table(m, False)
    rows = [th('الموظف', 'إجمالي الساعات', 'الإضافي', 'التأخير')]
    for e in S['emps']:
        a = o = s = 0
        for i in range(1, 13):
            r = stats(e, f'{y}-{i:02d}'); a += r['tw']; o += r['to']; s += r['ts']
        rows.append(td(e['name'], fm(a), fm(o), fm(s)))
    return page(b + '<h4>إجمالي السنة</h4>' + table(rows))
def auto_pdf():
    if not S['emps']: return
    m = key_today()[:7]
    to_pdf(page(h(f'تقرير الدوام الشهري — {mlabel(m)}') + month_table(m, False)), f'شهري/{m}.pdf')
    to_pdf(year_html(m[:4]), f'سنوي/{m[:4]}.pdf')
def safe(n): return re.sub(r'[\\/:*?"<>|]', '_', n)

# ---------- الواجهة ----------
QSS = """
* {font-family:'Segoe UI',Tahoma; font-size:10pt; color:#1d2540}
QMainWindow,#root{background:#f3f4f8}
#hdr{background:#232c4e} #hdr QLabel{color:white;background:transparent}
#bar{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00aeef,stop:.5 #ec008c,stop:1 #ffd400)}
QFrame[kind="card"]{background:white;border:1px solid #e3e6ee;border-radius:14px}
QFrame[kind="cardin"]{background:#f0faf6;border:1px solid #12805c;border-radius:14px}
QFrame[kind="stat"]{background:#f3f4f8;border:0;border-radius:10px}
QScrollArea{background:transparent;border:0}
QPushButton{background:#232c4e;color:white;border:0;border-radius:9px;padding:9px 18px;font-weight:600}
QPushButton:hover{background:#34407a}
QPushButton[kind="g"]{background:white;color:#555e7a;border:1px solid #d5d9e5;font-weight:normal}
QPushButton[kind="g"]:hover{background:#eef0f7}
QPushButton[kind="nav"]{background:white;color:#7a8299;border:1px solid #e3e6ee;padding:11px}
QPushButton[kind="nav"]:checked{background:#232c4e;color:white}
QPushButton[kind="in"]{background:#12805c;padding:12px;font-size:11pt}
QPushButton[kind="in"]:hover{background:#0e6b4d}
QPushButton[kind="out"]{background:#c0392b;padding:12px;font-size:11pt}
QPushButton[kind="out"]:hover{background:#a52f23}
QPushButton:disabled{background:#e3e6ee;color:#a3aabd;border:0}
#lock{background:#3a4575;border:1px solid #5a669c;color:white}
QLineEdit,QComboBox,QSpinBox{background:white;border:1px solid #d5d9e5;border-radius:9px;padding:8px;min-height:20px;selection-background-color:#232c4e}
QTableWidget{background:white;alternate-background-color:#f7f8fb;border:1px solid #e3e6ee;border-radius:10px;gridline-color:#eef0f5;selection-background-color:#dfe4f5;selection-color:#1d2540}
QHeaderView::section{background:#f3f4f8;color:#7a8299;border:0;padding:8px;font-weight:600}
QMessageBox,QInputDialog{background:white}
"""
def btn(text, cls='', cb=None):
    b = QPushButton(text); b.setProperty('kind', cls); b.setCursor(Qt.PointingHandCursor)
    if cb: b.clicked.connect(cb)
    return b
def card():
    f = QFrame(); f.setProperty('kind', 'card'); return f

class Logo(QWidget):
    def __init__(self): super().__init__(); self.setFixedSize(58, 36)
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        for i, c in enumerate(['#00aeef', '#ec008c', '#ffd400']):
            col = QColor(c); col.setAlpha(215); p.setBrush(col); p.setPen(Qt.NoPen); p.drawEllipse(2 + i * 16, 4, 28, 28)

class Main(QMainWindow):
    def __init__(self):
        super().__init__(); self.unlocked = False
        self.setWindowTitle(f'{OFFICE} - تسجيل الدوام'); self.resize(1000, 760)
        root = QWidget(); root.setObjectName('root'); self.setCentralWidget(root)
        v = QVBoxLayout(root); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
        # الرأس
        hd = QFrame(); hd.setObjectName('hdr'); hl = QHBoxLayout(hd); hl.setContentsMargins(22, 14, 22, 14)
        hl.addWidget(Logo()); tt = QVBoxLayout(); tt.setSpacing(0)
        a = QLabel(OFFICE); a.setStyleSheet('font-size:17pt;font-weight:700;color:white')
        b = QLabel('نظام تسجيل الدوام'); b.setStyleSheet('color:#aab2d5')
        tt.addWidget(a); tt.addWidget(b); hl.addLayout(tt); hl.addStretch()
        self.clock = QLabel(); self.clock.setStyleSheet('font-size:15pt;color:white;font-weight:600'); hl.addWidget(self.clock)
        self.lock = btn('🔒 المدير', cb=self.toggle_lock); self.lock.setObjectName('lock'); hl.addWidget(self.lock)
        v.addWidget(hd); bar = QFrame(); bar.setObjectName('bar'); bar.setFixedHeight(4); v.addWidget(bar)
        # التبويبات
        nav = QHBoxLayout(); nav.setContentsMargins(20, 14, 20, 0); self.grp = QButtonGroup(self)
        self.stack = QStackedWidget()
        for i, t in enumerate(['⏱️  الدوام اليوم', '📊  التقارير', '👥  الموظفون']):
            nb = btn(t, 'nav'); nb.setCheckable(True); nb.setChecked(i == 0); self.grp.addButton(nb, i); nav.addWidget(nb)
        self.grp.idClicked.connect(self.stack.setCurrentIndex)
        v.addLayout(nav); body = QVBoxLayout(); body.setContentsMargins(20, 14, 20, 20); body.addWidget(self.stack); v.addLayout(body, 1)
        self.stack.addWidget(self.page_today()); self.stack.addWidget(self.page_reports()); self.stack.addWidget(self.page_emps())
        t = QTimer(self); t.timeout.connect(self.tick); t.start(1000)
        self.deb = QTimer(self); self.deb.setSingleShot(True); self.deb.timeout.connect(self.safe_auto)
        self.refresh(); self.tick(); self.deb.start(500)

    def tick(self):
        n = datetime.now(); self.clock.setText(tm(n.timestamp() * 1000))
        if n.second == 0: self.build_cards()
    def safe_auto(self):
        try: auto_pdf()
        except Exception as e: print(e)
    def changed(self): save(); self.refresh(); self.deb.start(1500)

    # --- صفحة اليوم ---
    def page_today(self):
        w = card(); l = QVBoxLayout(w); l.setContentsMargins(18, 16, 18, 16)
        self.today = QLabel(); self.today.setStyleSheet('font-size:13pt;font-weight:600'); l.addWidget(self.today)
        self.ban = QLabel('🌴 الجمعة إجازة — أي دوام اليوم يُحسب كله وقتاً إضافياً')
        self.ban.setStyleSheet('background:#fff8dc;border:1px solid #f0dc8a;border-radius:9px;padding:9px'); l.addWidget(self.ban)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QFrame.NoFrame); sc.setStyleSheet('background:transparent')
        self.cw = QWidget(); self.cw.setStyleSheet('background:transparent'); self.grid = QGridLayout(self.cw)
        self.grid.setSpacing(14); sc.setWidget(self.cw); l.addWidget(sc); return w
    def build_cards(self):
        while self.grid.count():
            it = self.grid.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        if not S['emps']:
            self.grid.addWidget(QLabel('لا يوجد موظفون. أضفهم من تبويب «الموظفون».'), 0, 0)
        for i, e in enumerate(S['emps']):
            o = open_session(e['id']); c = QFrame(); c.setProperty('kind', 'cardin' if o else 'card')
            cl = QVBoxLayout(c); cl.setContentsMargins(16, 18, 16, 16); cl.setSpacing(8)
            av = QLabel(e['name'][:1]); av.setFixedSize(54, 54); av.setAlignment(Qt.AlignCenter)
            av.setStyleSheet('background:#232c4e;color:white;border-radius:27px;font-size:18pt;font-weight:700;border:0')
            nm = QLabel(e['name']); nm.setAlignment(Qt.AlignCenter); nm.setStyleSheet('font-size:12pt;font-weight:700;border:0;background:transparent')
            st = QLabel(f'حاضر منذ {tm(o["i"])}' if o else 'لم يسجّل حضوراً'); st.setAlignment(Qt.AlignCenter)
            st.setStyleSheet(f"color:{'#12805c' if o else '#7a8299'};border:0;background:transparent;font-weight:600")
            cl.addWidget(av, 0, Qt.AlignCenter); cl.addWidget(nm); cl.addWidget(st)
            row = QHBoxLayout(); bi = btn('✔ حضور', 'in', lambda _=0, x=e['id']: self.toggle(x)); bo = btn('⏏ انصراف', 'out', lambda _=0, x=e['id']: self.toggle(x))
            bi.setEnabled(not o); bo.setEnabled(bool(o)); row.addWidget(bi); row.addWidget(bo); cl.addLayout(row)
            self.grid.addWidget(c, i // 3, i % 3)
        self.grid.setRowStretch(self.grid.rowCount(), 1)
    def toggle(self, eid):
        o = open_session(eid); now = int(datetime.now().timestamp() * 1000)
        if o: o['o'] = now
        else: S['logs'].setdefault(eid, {}).setdefault(key_today(), []).append({'i': now, 'o': None})
        self.changed()

    # --- صفحة التقارير ---
    def page_reports(self):
        w = card(); l = QVBoxLayout(w); l.setContentsMargins(18, 16, 18, 16)
        r = QHBoxLayout(); self.re = QComboBox(); self.rmo = QComboBox(); self.rmo.addItems(MONTHS)
        self.ry = QSpinBox(); self.ry.setRange(2020, 2100); n = datetime.now()
        self.rmo.setCurrentIndex(n.month - 1); self.ry.setValue(n.year)
        for x in (self.re, self.rmo, self.ry): r.addWidget(x)
        for x in (self.re.currentIndexChanged, self.rmo.currentIndexChanged, self.ry.valueChanged): x.connect(self.rep)
        l.addLayout(r)
        self.tb = QTableWidget(0, 6); self.tb.setHorizontalHeaderLabels(['اليوم', 'أول حضور', 'آخر انصراف', 'المجموع', 'إضافي', 'تأخير / نقص'])
        self.tb.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.tb.verticalHeader().hide()
        self.tb.setEditTriggers(QAbstractItemView.NoEditTriggers); self.tb.setAlternatingRowColors(True); l.addWidget(self.tb, 1)
        sr = QHBoxLayout(); self.sv = []
        for t in ['إجمالي الساعات', 'الإضافي', 'التأخير', 'الراتب', 'المستحق']:
            f = QFrame(); f.setProperty('kind', 'stat'); fl = QVBoxLayout(f)
            a = QLabel(t); a.setAlignment(Qt.AlignCenter); a.setStyleSheet('color:#7a8299;font-size:9pt')
            b = QLabel('—'); b.setAlignment(Qt.AlignCenter); b.setStyleSheet('font-size:14pt;font-weight:700')
            fl.addWidget(a); fl.addWidget(b); sr.addWidget(f); self.sv.append(b)
        l.addLayout(sr)
        br = QHBoxLayout()
        for t, c, cb in [('💾 حفظ PDF شهري وسنوي', '', self.manual_auto), ('📄 خطاب للمدير 🔒', 'g', self.letter),
                         ('💰 كشف الرواتب 🔒', 'g', self.payroll), ('📁 فتح المجلد', 'g', self.open_dir)]:
            br.addWidget(btn(t, c, cb))
        l.addLayout(br); return w
    def cur_month(self): return f'{self.ry.value()}-{self.rmo.currentIndex() + 1:02d}'
    def cur_emp(self):
        i = self.re.currentIndex(); return S['emps'][i] if 0 <= i < len(S['emps']) else None
    def rep(self):
        e = self.cur_emp(); self.tb.setRowCount(0)
        if not e: return
        s = stats(e, self.cur_month()); self.tb.setRowCount(len(s['days']))
        for r, (k, c, f, l) in enumerate(s['days']):
            vals = [k[8:] + (' 🌴' if c['fri'] else ''), tm(f['i']), tm(l['o']) if l['o'] else '—', fm(c['tot']),
                    fm(c['over']) if c['over'] > 0 else '—', fm(c['short']) if c['short'] > 0 else '—']
            for j, x in enumerate(vals):
                it = QTableWidgetItem(x); it.setTextAlignment(Qt.AlignCenter)
                if j == 4 and c['over'] > 0: it.setForeground(QColor('#12805c'))
                if j == 5 and c['short'] > 0: it.setForeground(QColor('#c0392b'))
                self.tb.setItem(r, j, it)
        v = self.sv; v[0].setText(fm(s['tw'])); v[1].setText(fm(s['to'])); v[2].setText(fm(s['ts']))
        v[3].setText(money(e['salary']) if self.unlocked else '🔒'); v[4].setText(money(s['due']) if self.unlocked else '🔒')
    def manual_auto(self):
        try: auto_pdf(); QMessageBox.information(self, 'تم', f'تم حفظ التقارير (بدون رواتب) في:\n{DOCS}')
        except Exception as x: QMessageBox.warning(self, 'خطأ', str(x))
    def open_dir(self): DOCS.mkdir(parents=True, exist_ok=True); QDesktopServices.openUrl(QUrl.fromLocalFile(str(DOCS)))
    def payroll(self):
        if not self.need_mgr(): return
        m = self.cur_month(); f = to_pdf(page(h(f'كشف الرواتب — {mlabel(m)}') + month_table(m, True)), f'رواتب/كشف-الرواتب-{m}.pdf')
        QMessageBox.information(self, 'تم', f'تم حفظ كشف الرواتب:\n{f}')
    def letter(self):
        if not self.need_mgr(): return
        e = self.cur_emp(); m = self.cur_month()
        if not e: return
        s = stats(e, m)
        rows = [th('اليوم', 'أول حضور', 'آخر انصراف', 'المجموع', 'إضافي', 'تأخير')] + [
            td(k, tm(f['i']), tm(l['o']) if l['o'] else '—', fm(c['tot']), fm(c['over']), fm(c['short'])) for k, c, f, l in s['days']]
        body = (h('خطاب تقديم كشف الدوام') + f'<p>التاريخ: {datetime.now():%Y-%m-%d}</p><p>الفاضل / مدير {OFFICE} المحترم</p>'
            '<p>السلام عليكم ورحمة الله وبركاته،</p>' f'<p>أتقدم إليكم بكشف دوامي عن شهر <b>{mlabel(m)}</b>، وهذا ملخصه:</p>' +
            table([th('إجمالي الساعات', 'الإضافي', 'التأخير / النقص', 'الراتب', 'المبلغ المستحق'),
                   td(fm(s['tw']), fm(s['to']), fm(s['ts']), money(e['salary']), money(s['due']))]) +
            '<p>آمل التكرم بالاطلاع واعتماد المبلغ المستحق أعلاه، مع خالص الشكر والتقدير.</p><br>'
            f'<table width="100%"><tr><td>مقدّم الطلب: {e["name"]}<br><br>التوقيع: ..............</td><td align="left">اعتماد المدير<br><br>التوقيع: ..............</td></tr></table>'
            '<h4>تفاصيل الأيام</h4>' + table(rows))
        f = to_pdf(page(body), f'خطابات/{safe(e["name"])}-{m}.pdf')
        QMessageBox.information(self, 'تم', f'تم حفظ الخطاب:\n{f}')

    # --- صفحة الموظفين ---
    def page_emps(self):
        w = card(); l = QVBoxLayout(w); l.setContentsMargins(18, 16, 18, 16)
        r = QHBoxLayout(); self.nm = QLineEdit(); self.nm.setPlaceholderText('اسم الموظف'); self.sl = QLineEdit(); self.sl.setPlaceholderText('الراتب الشهري')
        r.addWidget(self.nm, 2); r.addWidget(self.sl, 1); r.addWidget(btn('➕ إضافة', cb=self.add_emp)); l.addLayout(r)
        self.et = QTableWidget(0, 3); self.et.setHorizontalHeaderLabels(['الاسم', 'الراتب', 'إجراءات'])
        self.et.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.et.verticalHeader().hide()
        self.et.verticalHeader().setDefaultSectionSize(48); self.et.setEditTriggers(QAbstractItemView.NoEditTriggers); l.addWidget(self.et); return w
    def add_emp(self):
        n = self.nm.text().strip()
        if not n: return
        try: sal = float(self.sl.text() or 0) if self.unlocked else 0
        except ValueError: sal = 0
        S['emps'].append({'id': uuid.uuid4().hex[:10], 'name': n, 'salary': sal}); self.nm.clear(); self.sl.clear(); self.changed()
    def set_sal(self, eid):
        e = next(x for x in S['emps'] if x['id'] == eid)
        v, ok = QInputDialog.getDouble(self, 'الراتب', f'الراتب الشهري لـ {e["name"]}', e['salary'], 0, 10**7, 2)
        if ok: e['salary'] = v; self.changed()
    def del_emp(self, eid):
        if not self.need_mgr(): return
        if QMessageBox.question(self, 'تأكيد', 'حذف الموظف وكل سجلاته؟') == QMessageBox.Yes:
            S['emps'] = [x for x in S['emps'] if x['id'] != eid]; S['logs'].pop(eid, None); self.changed()

    # --- المدير ---
    def need_mgr(self):
        if not self.unlocked: self.toggle_lock()
        return self.unlocked
    def toggle_lock(self):
        if self.unlocked: self.unlocked = False; return self.refresh()
        sha = lambda s: hashlib.sha256(('fkra' + s).encode()).hexdigest()
        if not S['pin']:
            a, ok = QInputDialog.getText(self, 'رمز المدير', 'عيّن رمزاً سرياً (4 خانات فأكثر):', QLineEdit.Password)
            if not ok or len(a) < 4: return
            S['pin'] = sha(a); save()
        else:
            a, ok = QInputDialog.getText(self, 'رمز المدير', 'أدخل الرمز السري:', QLineEdit.Password)
            if not ok: return
            if sha(a) != S['pin']: return QMessageBox.warning(self, 'خطأ', 'الرمز غير صحيح')
        self.unlocked = True; self.refresh()

    def refresh(self):
        self.lock.setText('🔓 وضع المدير (اضغط للقفل)' if self.unlocked else '🔒 المدير')
        n = datetime.now(); self.today.setText(f'{["الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"][n.weekday()]}  {n.day} {MONTHS[n.month - 1]} {n.year}')
        self.ban.setVisible(n.weekday() == 4); self.sl.setVisible(self.unlocked); self.build_cards()
        i = self.re.currentIndex(); self.re.blockSignals(True); self.re.clear(); self.re.addItems([e['name'] for e in S['emps']])
        self.re.setCurrentIndex(min(max(i, 0), max(len(S['emps']) - 1, 0))); self.re.blockSignals(False)
        self.et.setRowCount(len(S['emps']))
        for r, e in enumerate(S['emps']):
            for j, x in enumerate([e['name'], money(e['salary']) if self.unlocked else '🔒 مخفي']):
                it = QTableWidgetItem(x); it.setTextAlignment(Qt.AlignCenter); self.et.setItem(r, j, it)
            c = QWidget(); cl = QHBoxLayout(c); cl.setContentsMargins(4, 4, 4, 4)
            if self.unlocked: cl.addWidget(btn('تعديل الراتب', 'g', lambda _=0, x=e['id']: self.set_sal(x)))
            cl.addWidget(btn('حذف', 'g', lambda _=0, x=e['id']: self.del_emp(x))); self.et.setCellWidget(r, 2, c)
        self.rep()

if __name__ == '__main__':
    load(); app = QApplication(sys.argv); app.setLayoutDirection(Qt.RightToLeft)
    app.setStyle('Fusion')
    try: app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except Exception: pass
    p = QPalette()
    for r, c in [(QPalette.Window, '#f3f4f8'), (QPalette.WindowText, '#1d2540'), (QPalette.Base, '#ffffff'), (QPalette.AlternateBase, '#f7f8fb'),
                 (QPalette.Text, '#1d2540'), (QPalette.Button, '#ffffff'), (QPalette.ButtonText, '#1d2540'), (QPalette.Highlight, '#232c4e'),
                 (QPalette.HighlightedText, '#ffffff'), (QPalette.ToolTipBase, '#ffffff'), (QPalette.ToolTipText, '#1d2540')]:
        p.setColor(r, QColor(c))
    app.setPalette(p); app.setFont(QFont('Segoe UI', 10)); app.setStyleSheet(QSS)
    w = Main(); w.show(); sys.exit(app.exec())
