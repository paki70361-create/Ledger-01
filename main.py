import sqlite3
from datetime import datetime
from pathlib import Path

from kivy.app import App
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup

BG = (0.95, 0.96, 0.98, 1)
NAVY = (0.08, 0.13, 0.22, 1)
BLUE = (0.13, 0.35, 0.82, 1)
TEXT = (0.10, 0.14, 0.22, 1)
MUTED = (0.40, 0.45, 0.53, 1)
RED = (0.72, 0.18, 0.18, 1)

class LedgerApp(App):
    def build(self):
        self.title = "Personal Ledger"
        Window.clearcolor = BG
        db_path = Path(self.user_data_dir) / "personal_ledger.db"
        self.db = sqlite3.connect(str(db_path))
        self.db.execute("""CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person TEXT NOT NULL, amount REAL NOT NULL,
            kind TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL)""")
        self.db.commit()

        page = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(9))
        header = BoxLayout(orientation="vertical", size_hint_y=None,
                           height=dp(70), padding=[dp(14), dp(8)])
        with header.canvas.before:
            Color(*NAVY)
            self.header_bg = RoundedRectangle(pos=header.pos, size=header.size, radius=[dp(12)])
        header.bind(pos=lambda w, p: setattr(self.header_bg, "pos", p),
                    size=lambda w, s: setattr(self.header_bg, "size", s))
        header.add_widget(Label(
            text="[b]PERSONAL LEDGER[/b]\n[size=12]Your simple money record book[/size]",
            markup=True, color=(1,1,1,1), halign="left", valign="middle"))
        page.add_widget(header)

        summary = GridLayout(cols=3, size_hint_y=None, height=dp(72), spacing=dp(5))
        self.given_total = self.summary_card(summary, "TOTAL GIVEN")
        self.received_total = self.summary_card(summary, "TOTAL RECEIVED")
        self.net_total = self.summary_card(summary, "NET BALANCE")
        page.add_widget(summary)

        form = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(244), spacing=dp(6))
        form.add_widget(self.section("ADD TRANSACTION"))
        self.person = self.input_box("Person's name")
        self.amount = self.input_box("Amount", numeric=True)
        self.kind = Spinner(text="Given", values=("Given", "Received"),
                            size_hint_y=None, height=dp(41),
                            background_normal="", background_color=(0.89,0.92,0.97,1),
                            color=TEXT)
        self.reason = self.input_box("Reason / transaction details")
        for w in (self.person, self.amount, self.kind, self.reason):
            form.add_widget(w)
        save = Button(text="SAVE TRANSACTION", size_hint_y=None, height=dp(43),
                      background_normal="", background_color=BLUE, color=(1,1,1,1), bold=True)
        save.bind(on_release=self.add_transaction)
        form.add_widget(save)
        page.add_widget(form)

        page.add_widget(self.section("TRANSACTION HISTORY"))
        self.search = TextInput(hint_text="Search by name or reason", multiline=False,
                                size_hint_y=None, height=dp(40),
                                background_normal="", background_active="",
                                background_color=(1,1,1,1), foreground_color=TEXT,
                                padding=[dp(10),dp(9)])
        self.search.bind(text=lambda *_: self.refresh())
        page.add_widget(self.search)

        self.records = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.records.bind(minimum_height=self.records.setter("height"))
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(self.records)
        page.add_widget(scroll)
        self.refresh()
        return page

    def section(self, title):
        return Label(text=f"[b]{title}[/b]", markup=True, color=TEXT,
                     size_hint_y=None, height=dp(23), halign="left", valign="middle")

    def input_box(self, hint, numeric=False):
        return TextInput(hint_text=hint, multiline=False,
                         input_filter="float" if numeric else None,
                         size_hint_y=None, height=dp(41),
                         padding=[dp(10),dp(9)], background_normal="",
                         background_active="", background_color=(1,1,1,1),
                         foreground_color=TEXT, cursor_color=BLUE)

    def summary_card(self, parent, title):
        box = BoxLayout(orientation="vertical", padding=dp(4))
        label = Label(text=f"[size=10]{title}[/size]\n[b]0.00[/b]",
                      markup=True, color=TEXT, halign="center", valign="middle")
        box.add_widget(label)
        parent.add_widget(box)
        return label

    def popup_message(self, title, message):
        Popup(title=title, content=Label(text=message),
              size_hint=(0.84,0.28)).open()

    def add_transaction(self, *_):
        person = self.person.text.strip()
        raw_amount = self.amount.text.strip().replace(",", "")
        reason = self.reason.text.strip()
        if not person or not raw_amount or not reason:
            self.popup_message("Missing details", "Enter name, amount and reason.")
            return
        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self.popup_message("Invalid amount", "Enter an amount greater than zero.")
            return
        self.db.execute(
            "INSERT INTO transactions(person,amount,kind,reason,created_at) VALUES(?,?,?,?,?)",
            (person, amount, self.kind.text, reason, datetime.now().strftime("%d %b %Y, %I:%M %p")))
        self.db.commit()
        self.person.text = ""
        self.amount.text = ""
        self.reason.text = ""
        self.kind.text = "Given"
        self.refresh()
        self.popup_message("Saved", "Transaction saved on this phone.")

    def refresh(self):
        if not hasattr(self, "records"):
            return
        self.records.clear_widgets()
        rows = self.db.execute(
            "SELECT id,person,amount,kind,reason,created_at FROM transactions ORDER BY id DESC"
        ).fetchall()
        given = sum(r[2] for r in rows if r[3] == "Given")
        received = sum(r[2] for r in rows if r[3] == "Received")
        self.given_total.text = f"[size=10]TOTAL GIVEN[/size]\n[b]{given:,.2f}[/b]"
        self.received_total.text = f"[size=10]TOTAL RECEIVED[/size]\n[b]{received:,.2f}[/b]"
        self.net_total.text = f"[size=10]NET BALANCE[/size]\n[b]{received-given:,.2f}[/b]"
        term = self.search.text.strip().lower()
        count = 0
        for rid, person, amount, kind, reason, stamp in rows:
            if term and term not in person.lower() and term not in reason.lower():
                continue
            count += 1
            row = BoxLayout(size_hint_y=None, height=dp(86), padding=dp(7), spacing=dp(6))
            info = Label(text=f"[b]{person}[/b] • {kind}\n{amount:,.2f} | {reason}\n[size=10]{stamp}[/size]",
                         markup=True, color=TEXT, halign="left", valign="middle")
            info.bind(size=lambda w,s: setattr(w,"text_size",s))
            row.add_widget(info)
            delete = Button(text="DELETE", size_hint_x=None, width=dp(72),
                            background_normal="", background_color=RED, color=(1,1,1,1))
            delete.bind(on_release=lambda btn, txid=rid: self.confirm_delete(txid))
            row.add_widget(delete)
            self.records.add_widget(row)
        if count == 0:
            self.records.add_widget(Label(text="No transactions found.", color=MUTED,
                                          size_hint_y=None, height=dp(50)))

    def confirm_delete(self, txid):
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        content.add_widget(Label(text="Delete this transaction permanently?"))
        buttons = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        popup = Popup(title="Confirm deletion", content=content, size_hint=(0.84,0.28))
        yes = Button(text="Delete", background_normal="", background_color=RED)
        no = Button(text="Cancel")
        buttons.add_widget(yes)
        buttons.add_widget(no)
        content.add_widget(buttons)
        def remove(*_):
            self.db.execute("DELETE FROM transactions WHERE id=?", (txid,))
            self.db.commit()
            popup.dismiss()
            self.refresh()
        yes.bind(on_release=remove)
        no.bind(on_release=popup.dismiss)
        popup.open()

    def on_stop(self):
        if hasattr(self, "db"):
            self.db.close()

if __name__ == "__main__":
    LedgerApp().run()
