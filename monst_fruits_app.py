import sqlite3
from datetime import datetime
import csv
import io
import streamlit as st

DB_PATH = "monst_fruits.db"


# -----------------------
# DB
# -----------------------
GRADE_OPTIONS = ["", "EL", "特L"]
FRUIT_OPTIONS = [
    "",
    "同族加撃",
    "同族加命",
    "同族加撃速",
    "撃種加撃",
    "撃種加命",
    "撃種加撃速",
    "戦型加撃",
    "戦型加命",
    "戦型加撃速",
    "熱き友撃",
    "速必殺",
    "将命削り",
    "兵命削り",
    "ケガ減り",
    "ちび癒し",
    "毒がまん",
    "麻痺がまん",
    "不屈の必殺",
    "不屈の防御",
    "学び",
    "スコア稼ぎ",
    "Sランク",
    "荒稼ぎ",
]

def safe_index(options, value):
    return options.index(value) if value in options else 0
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

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
        fruit4 TEXT,
        note TEXT,
        updated_at TEXT NOT NULL
        );
        """
    )

    # 既存DB用（fruit4なければ追加）
    try:
        conn.execute("ALTER TABLE entries ADD COLUMN fruit4 TEXT;")
    except:
        pass

    conn.commit()
    conn.close()

def add_entry(account, character, fruit1, fruit2, fruit3, fruit4, note):
    conn = get_conn()
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO entries (account, character, fruit1, fruit2, fruit3, fruit4, note, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (account, character, fruit1, fruit2, fruit3, fruit4, note, now),
    )
    conn.commit()
    conn.close()

def fetch_entries(account=None, char_q=None, fruit_q=None, note_q=None):
    conn = get_conn()
    q = """
        SELECT id, account, character, fruit1, fruit2, fruit3, fruit4, note, updated_at
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
        q += " AND (fruit1 LIKE ? OR fruit2 LIKE ? OR fruit3 LIKE ? OR fruit4 LIKE ?)"
        params.extend([f"%{fruit_q}%"] * 4)

    if note_q:
        q += " AND note LIKE ?"
        params.append(f"%{note_q}%")

    q += " ORDER BY account ASC, character ASC, updated_at DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows

def insert_many(rows):
    conn = get_conn()
    now = datetime.now().isoformat(timespec="seconds")
    conn.executemany(
        """
        INSERT INTO entries (account, character, fruit1, fruit2, fruit3, fruit4, note, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        [
            (
                (r.get("account") or "main"),
                (r.get("character") or ""),
                (r.get("fruit1") or None),
                (r.get("fruit2") or None),
                (r.get("fruit3") or None),
                (r.get("fruit4") or None),
                (r.get("note") or None),
                now,
            )
            for r in rows
            if (r.get("character") or "").strip() != ""
        ],
    )
    conn.commit()
    conn.close()

def update_entry(entry_id, fruit1, fruit2, fruit3, fruit4, note):
    conn = get_conn()
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """
        UPDATE entries
        SET fruit1 = ?, fruit2 = ?, fruit3 = ?, fruit4 = ?, note = ?, updated_at = ?
        WHERE id = ?;
        """,
        (fruit1, fruit2, fruit3, fruit4, note, now, entry_id),
    )
    conn.commit()
    conn.close()

def combine(fruit, grade):
    if not fruit:
        return None
    return f"{fruit}{grade}" if grade else fruit

def split_fruit_and_grade(value):
    if not value:
        return "", ""
    if value.endswith("EL"):
        return value[:-2], "EL"
    if value.endswith("特L"):
        return value[:-2], "特L"
    return value, ""

# -----------------------
# CSV helpers
# -----------------------
CSV_HEADERS = ["account", "character", "fruit1", "fruit2", "fruit3", "fruit4", "note"]

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
                "fruit4": r[6] or "",
                "note": r[7] or "",
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

# -----------------------
# 追加
# -----------------------
with tabs[0]:
    st.subheader("追加")
    col1, col2 = st.columns([1, 2])

    ADD_KEYS = [
    "add_character",
    "add_fruit1", "add_fruit2", "add_fruit3", "add_fruit4",
    "add_grade1", "add_grade2", "add_grade3", "add_grade4",
    "add_note"
]

    def clear_add_inputs():
        for k in ADD_KEYS:
            st.session_state[k] = ""

    def save_entry_cb():
        account = st.session_state.get("add_account", "main")
        character = st.session_state.get("add_character", "")
        fruit1 = combine(
            st.session_state.get("add_fruit1", ""),
            st.session_state.get("add_grade1", "")
        )

        fruit2 = combine(
            st.session_state.get("add_fruit2", ""),
            st.session_state.get("add_grade2", "")
        )

        fruit3 = combine(
            st.session_state.get("add_fruit3", ""),
            st.session_state.get("add_grade3", "")
        )
        fruit4 = combine(
            st.session_state.get("add_fruit4", ""),
            st.session_state.get("add_grade4", "")
        )
        note = st.session_state.get("add_note", "")

        if not character.strip():
            st.session_state["add_error"] = "キャラ名は必須！"
            st.session_state["add_success"] = ""
            return

        add_entry(
            account=account.strip(),
            character=character.strip(),
            fruit1=fruit1,
            fruit2=fruit2,
            fruit3=fruit3,
            fruit4=fruit4,
            note=note.strip() or None,
        )

        clear_add_inputs()
        st.session_state["add_error"] = ""
        st.session_state["add_success"] = "保存した！"

    with col1:
        st.selectbox("アカウント", accounts, index=0, key="add_account")
        st.text_input("キャラ名（必須）", key="add_character")
        col_f1, col_g1 = st.columns([2,1])
        with col_f1:
            fruit1 = st.selectbox("実1", FRUIT_OPTIONS, key="add_fruit1")
        with col_g1:
            grade1 = st.selectbox("等級", GRADE_OPTIONS, key="add_grade1")
        col_f2, col_g2 = st.columns([2,1])
        with col_f2:
            fruit2 = st.selectbox("実2", FRUIT_OPTIONS, key="add_fruit2")
        with col_g2:
            grade2 = st.selectbox("等級", GRADE_OPTIONS, key="add_grade2")

        col_f3, col_g3 = st.columns([2,1])
        with col_f3:
            fruit3 = st.selectbox("実3", FRUIT_OPTIONS, key="add_fruit3")
        with col_g3:
         grade3 = st.selectbox("等級", GRADE_OPTIONS, key="add_grade3")
        col_f4, col_g4 = st.columns([2,1])
        with col_f4:
            fruit4 = st.selectbox("実4", FRUIT_OPTIONS, key="add_fruit4")
        with col_g4:
            grade4 = st.selectbox("等級", GRADE_OPTIONS, key="add_grade4")
        st.text_area("メモ（任意）", key="add_note", height=80)
        st.button("保存", type="primary", on_click=save_entry_cb)

        if st.session_state.get("add_error"):
            st.error(st.session_state["add_error"])
        if st.session_state.get("add_success"):
            st.success(st.session_state["add_success"])

    with col2:
        st.info("表記ゆれがあると検索が面倒になるから、キャラ名はできるだけ統一がおすすめ。")
        st.write("例：")
        st.code("main / ルシファー / 同族加撃 / 速必殺 / 将命削り", language="text")

# -----------------------
# 検索
# -----------------------
with tabs[1]:
    st.subheader("検索（部分一致OK）")
    c1, c2, c3, c4 = st.columns([1, 2, 2, 2])
    with c1:
        account_s = st.selectbox("アカウント", ["ALL"] + accounts, index=0)
    with c2:
        char_q = st.text_input("キャラ名で検索", value="")
    with c3:
        fruit_q = st.text_input("実で検索（例：加撃 / 速必殺 / 将命）", value="")
    with c4:
        note_q = st.text_input("メモで検索（あとがき）", value="")

    rows = fetch_entries(
        account=account_s,
        char_q=char_q.strip() or None,
        fruit_q=fruit_q.strip() or None,
        note_q=note_q.strip() or None,
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
                    "fruit4": r[6] or "",
                    "note": r[7] or "",
                    "updated_at": r[8],
                }
                for r in rows
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("該当なし")

# -----------------------
# 一覧 + 編集
# -----------------------
with tabs[2]:
    st.subheader("一覧")
    account_l = st.selectbox("一覧アカウント", ["ALL"] + accounts, index=0)
    rows = fetch_entries(account=account_l)

    st.write(f"件数：{len(rows)}")
    if rows:
        st.dataframe(
            [
                {
                    "id": r[0],
                    "account": r[1],
                    "character": r[2],
                    "fruit1": r[3] or "",
                    "fruit2": r[4] or "",
                    "fruit3": r[5] or "",
                    "fruit4": r[6] or "",
                    "note": r[7] or "",
                    "updated_at": r[8],
                }
                for r in rows
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.subheader("✏ 編集（実・メモ）")

        options = [(r[0], f"{r[1]} / {r[2]}（更新:{r[8]}）") for r in rows]
        selected_id = st.selectbox(
            "編集するキャラを選択",
            options=options,
            format_func=lambda x: x[1],
            key="edit_target",
        )[0]

        selected_row = next(r for r in rows if r[0] == selected_id)

        #分解
        fruit1_name, grade1 = split_fruit_and_grade(selected_row[3])
        fruit2_name, grade2 = split_fruit_and_grade(selected_row[4])
        fruit3_name, grade3 = split_fruit_and_grade(selected_row[5])
        fruit4_name, grade4 = split_fruit_and_grade(selected_row[6])
        

        with st.form("edit_form"):
            e_fruit1 = st.selectbox(
                "実1",
                FRUIT_OPTIONS,
                index=safe_index(FRUIT_OPTIONS, fruit1_name),
                key="edit_f1"
            )
            e_grade1 = st.selectbox(
                "等級1",
                GRADE_OPTIONS,
                index=safe_index(GRADE_OPTIONS, grade1),
            )
            e_fruit2 = st.selectbox(
                "実2",
                FRUIT_OPTIONS,
                index=safe_index(FRUIT_OPTIONS, fruit2_name),
                key="edit_f2"
            )
            e_grade2 = st.selectbox(
                "等級2",
                GRADE_OPTIONS,
                index=safe_index(GRADE_OPTIONS, grade2),
            )

            e_fruit3 = st.selectbox(
                "実3",
                FRUIT_OPTIONS,
                index=safe_index(FRUIT_OPTIONS, fruit3_name),
                key="edit_f3"
            )
            e_grade3 = st.selectbox(
                "等級3",
                GRADE_OPTIONS,
                index=safe_index(GRADE_OPTIONS, grade3),
            )
            e_fruit4 = st.selectbox(
                "実4",
                FRUIT_OPTIONS,
                index=safe_index(FRUIT_OPTIONS, fruit4_name),
                key="edit_f4"
            )
            e_grade4 = st.selectbox(
                "等級4",
                GRADE_OPTIONS,
                index=safe_index(GRADE_OPTIONS, grade4),
            )
            e_note = st.text_area("メモ（あとがき）", value=selected_row[7] or "", height=80, key="edit_note")

            submitted = st.form_submit_button("この内容で更新")
            if submitted:
                update_entry(
                    entry_id=selected_id,
                    fruit1=combine(e_fruit1, e_grade1),
                    fruit2=combine(e_fruit2, e_grade2),
                    fruit3=combine(e_fruit3, e_grade3),
                    fruit4=combine(e_fruit4, e_grade4),
                    note=e_note.strip() or None,
                )
                st.success("更新した！")
                st.rerun()
    else:
        st.info("まだ登録なし")

# -----------------------
# バックアップ
# -----------------------
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
            missing = [h for h in CSV_HEADERS if h not in rows_in[0]]
            if missing:
                st.error(f"CSVの列が足りない：{missing}")
            else:
                if st.button("取り込み実行", type="primary"):
                    insert_many(rows_in)
                    st.success(f"取り込み完了！（{len(rows_in)}行） 一覧/検索タブで確認してね。")
        except Exception as e:
            st.error(f"読み込み失敗：{e}")
