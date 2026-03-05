import sqlite3
from datetime import datetime
import csv
import io
import streamlit as st

DB_PATH = "monst_fruits.db"

# -----------------------
# DB
# -----------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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

def fetch_entries(account=None, char_q=None, fruit_q=None):
    conn = get_conn()
    q = """
        SELECT id, account, character, fruit1, fruit2, fruit3, note, updated_at
        FROM entries
        WHERE 1=1
    """
    params = []

    if account and account != "ALL":
        q += " AND account = ?"
        params.append(account)

    if char_q:
        q += " AND character LIKE ?"
        params.append(f"%{char_q}%")

    if fruit_q:
        q += " AND (fruit1 LIKE ? OR fruit2 LIKE ? OR fruit3 LIKE ?)"
        params.extend([f"%{fruit_q}%"] * 3)

    q += " ORDER BY account ASC, character ASC, updated_at DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows

def insert_many(rows):
    """rows: list of dict with keys account, character, fruit1, fruit2, fruit3, note"""
    conn = get_conn()
    now = datetime.now().isoformat(timespec="seconds")
    conn.executemany(
        """
        INSERT INTO entries (account, character, fruit1, fruit2, fruit3, note, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        [
            (
                r.get("account") or "main",
                r.get("character") or "",
                r.get("fruit1") or None,
                r.get("fruit2") or None,
                r.get("fruit3") or None,
                r.get("note") or None,
                now,
            )
            for r in rows
            if (r.get("character") or "").strip() != ""
        ],
    )
    conn.commit()
    conn.close()

# -----------------------
# CSV helpers
# -----------------------
CSV_HEADERS = ["account", "character", "fruit1", "fruit2", "fruit3", "note"]

def rows_to_csv_bytes(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_HEADERS)
    writer.writeheader()
    for r in rows:
        writer.writerow(
            {
                "account": r[1],
                "character": r[2],
                "fruit1": r[3] or "",
                "fruit2": r[4] or "",
                "fruit3": r[5] or "",
                "note": r[6] or "",
            }
        )
    return output.getvalue().encode("utf-8")

def csv_file_to_rows(uploaded_file):
    text = uploaded_file.read().decode("utf-8")
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    rows = []
    for row in reader:
        rows.append({k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()})
    return rows

# -----------------------
# UI
# -----------------------
st.set_page_config(page_title="モンスト実管理", layout="wide")
init_db()

st.title("📌 モンスト：わくわくの実 管理（3垢OK）")
st.caption("※クラウドは再起動等でDBが消える可能性があるから、CSVバックアップ推奨。")

accounts = ["main", "sub1", "sub2"]
tabs = st.tabs(["➕ 追加", "🔎 検索", "📋 一覧", "💾 バックアップ"])

with tabs[0]:
    st.subheader("追加")
    col1, col2 = st.columns([1, 2])

    with col1:
        account = st.selectbox("アカウント", accounts, index=0)
        character = st.text_input("キャラ名（必須）")
        fruit1 = st.text_input("実1（例：同族加撃）", value="")
        fruit2 = st.text_input("実2", value="")
        fruit3 = st.text_input("実3", value="")
        note = st.text_area("メモ（任意）", value="", height=80)

        if st.button("保存", type="primary"):
            if not character.strip():
                st.error("キャラ名は必須！")
            else:
                add_entry(
                    account=account.strip(),
                    character=character.strip(),
                    fruit1=fruit1.strip() or None,
                    fruit2=fruit2.strip() or None,
                    fruit3=fruit3.strip() or None,
                    note=note.strip() or None,
                )
                st.success("保存した！")

    with col2:
        st.info("表記ゆれがあると検索が面倒になるから、キャラ名はできるだけ統一がおすすめ。")
        st.write("例：")
        st.code(
            "main / ルシファー / 同族加撃 / 速必殺 / 将命削り",
            language="text",
        )

with tabs[1]:
    st.subheader("検索（部分一致OK）")
    c1, c2, c3 = st.columns([1, 2, 2])
    with c1:
        account_s = st.selectbox("アカウント", ["ALL"] + accounts, index=0)
    with c2:
        char_q = st.text_input("キャラ名で検索", value="")
    with c3:
        fruit_q = st.text_input("実で検索（例：加撃 / 速必殺 / 将命）", value="")

    rows = fetch_entries(
        account=account_s,
        char_q=char_q.strip() or None,
        fruit_q=fruit_q.strip() or None,
    )

    st.write(f"件数：{len(rows)}")
    if rows:
        st.dataframe(
            [
                {
                    "account": r[1],
                    "character": r[2],
                    "fruit1": r[3] or "",
                    "fruit2": r[4] or "",
                    "fruit3": r[5] or "",
                    "note": r[6] or "",
                    "updated_at": r[7],
                }
                for r in rows
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("該当なし")

with tabs[2]:
    st.subheader("一覧")
    account_l = st.selectbox("一覧アカウント", ["ALL"] + accounts, index=0)
    rows = fetch_entries(account=account_l)

    st.write(f"件数：{len(rows)}")
    if rows:
        st.dataframe(
            [
                {
                    "account": r[1],
                    "character": r[2],
                    "fruit1": r[3] or "",
                    "fruit2": r[4] or "",
                    "fruit3": r[5] or "",
                    "note": r[6] or "",
                    "updated_at": r[7],
                }
                for r in rows
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("まだ登録なし")

with tabs[3]:
    st.subheader("バックアップ（CSV）")

    st.markdown("### ✅ CSVダウンロード（バックアップ）")
    all_rows = fetch_entries(account="ALL")
    csv_bytes = rows_to_csv_bytes(all_rows)
    st.download_button(
        label="CSVをダウンロード",
        data=csv_bytes,
        file_name="monst_fruits_backup.csv",
        mime="text/csv",
    )

    st.divider()

    st.markdown("### 📥 CSVから復元（取り込み）")
    st.caption("同じキャラが二重登録になってもOKな仕様（まずはシンプル優先）。必要なら後で『上書き更新』に改造できる。")

    uploaded = st.file_uploader("CSVを選択", type=["csv"])
    if uploaded is not None:
        try:
            rows_in = csv_file_to_rows(uploaded)
            # 簡単チェック：必要な列があるか
            missing = [h for h in CSV_HEADERS if h not in rows_in[0]]
            if missing:
                st.error(f"CSVの列が足りない：{missing}")
            else:
                if st.button("取り込み実行", type="primary"):
                    insert_many(rows_in)
                    st.success(f"取り込み完了！（{len(rows_in)}行） 一覧/検索タブで確認してね。")
        except Exception as e:
            st.error(f"読み込み失敗：{e}")
