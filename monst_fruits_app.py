import sqlite3
from datetime import datetime
import streamlit as st

DB_PATH = "monst_fruits.db"

# -----------------------
# DB
# -----------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account TEXT NOT NULL,
            character TEXT NOT NULL,
            fruit1 TEXT,
            fruit2 TEXT,
            fruit3 TEXT,
            note TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()

def add_entry(account, character, fruit1, fruit2, fruit3, note):
    conn = get_conn()
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO entries (account, character, fruit1, fruit2, fruit3, note, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (account, character, fruit1, fruit2, fruit3, note, now),
    )
    conn.commit()
    conn.close()

def fetch_entries():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, account, character, fruit1, fruit2, fruit3, note, updated_at FROM entries"
    ).fetchall()
    conn.close()
    return rows

# -----------------------
# UI
# -----------------------
st.set_page_config(page_title="モンスト実管理")

init_db()

st.title("モンスト わくわくの実 管理")

accounts = ["main", "sub1", "sub2"]

tab1, tab2 = st.tabs(["追加", "一覧"])

with tab1:
    st.subheader("キャラ登録")

    account = st.selectbox("アカウント", accounts)
    character = st.text_input("キャラ名")

    fruit1 = st.text_input("実1")
    fruit2 = st.text_input("実2")
    fruit3 = st.text_input("実3")

    note = st.text_area("メモ")

    if st.button("保存"):
        if character.strip() == "":
            st.error("キャラ名を入力して")
        else:
            add_entry(account, character, fruit1, fruit2, fruit3, note)
            st.success("保存した！")

with tab2:
    st.subheader("登録一覧")

    rows = fetch_entries()

    if rows:
        for r in rows:
            st.write(
                f"【{r[1]}】 {r[2]} | {r[3]} / {r[4]} / {r[5]} | {r[6]} | 更新:{r[7]}"
            )
    else:
        st.info("まだ登録なし")