#!/usr/bin/env python3
"""src/plan-a.html（原本・1枚もの）から、独立した各ページを生成する。

**生成物を直接編集しないこと。** 原本を直して `python3 build.py` を走らせる。
生成物だけを git revert しても次のビルドで元に戻ってしまうため、
原本と生成物は必ず一緒にコミットする（かみのてで踏んだ事故）。

出力:
  index.html    トップ（原本そのまま＋各節に「詳しく見る」を挿す）
  service.html  ご紹介できる人材
  support.html  登録支援機関としての支援
  flow.html     受入れまでの流れ
  partners.html 自社グループと提携機関
  company.html  企業情報（代表ごあいさつ＋会社概要）
  faq.html      よくあるご質問
  news.html     過去のお知らせ（src/news.json から。旧サイトの全13件）
  contact.html  お問い合わせ
  privacy.html  プライバシーポリシー（旧サイトの本文を入れるまでは枠だけ）
"""
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src"

# 案 → (原本, 一言)。**ページ構成は案で変えない**（比べられなくなるため）。
PLANS = {
    "a": ("plan-a.html", "明朝と余白で、落ち着いた品位を"),
    "b": ("plan-b.html", "青とゴシックで、明快に"),
}

# 出力ファイル → (原本の節id, メニュー表示名, ページ見出し, 英字ラベル, 説明)
PAGES = {
    "service.html":  ("visas",    "ご紹介できる人材", "ご紹介できる人材", "SERVICE",
                      "就労が可能な5つの在留資格すべてに対応しています。"),
    "support.html":  ("support",  "支援内容",       "登録支援機関としての支援", "SUPPORT",
                      "特定技能で義務づけられている支援です。"),
    "flow.html":     ("flow",     "受入れの流れ",   "受入れまでの流れ", "FLOW",
                      "ご相談から就労開始までの目安です。"),
    "partners.html": ("partners", "提携機関",       "自社グループと提携機関", "GROUP & PARTNERS",
                      "監理団体を自社で設立しているため、一貫してお引き受けできます。"),
    "company.html":  ("company",  "企業情報",       "企業情報", "COMPANY",
                      "会社の概要と、代表からのごあいさつです。"),
    "faq.html":      ("faq",      "よくあるご質問", "よくあるご質問", "FAQ",
                      "費用や期間など、はじめてのご検討でよくいただくご質問です。"),
}
# メニューの並び（左3つ／ロゴ／右3つ）
NAV_L = [("service.html", "ご紹介できる人材"), ("support.html", "支援内容"), ("flow.html", "受入れの流れ")]
NAV_R = [("partners.html", "提携機関"), ("company.html", "企業情報"), ("contact.html", "お問い合わせ")]

# 節id → 出力ファイル。原本のアンカーをページへの参照に張り替えるのに使う
ANCHOR = {sec: out for out, (sec, *_ ) in PAGES.items()}
ANCHOR["contact"] = "contact.html"

EXTRA_CSS = """
/* ---- 下層ページの見出し（build.py が差し込む） ---- */
.page-head{padding:64px 0 0; text-align:center}
.page-head .en{font-family:var(--serif); font-weight:300; color:var(--gold);
  font-size:12px; letter-spacing:.28em; display:block; margin-bottom:14px}
.page-head h1{font-family:var(--serif); font-weight:300; font-size:clamp(23px,3.2vw,31px);
  letter-spacing:.16em; margin:0 0 14px}
.page-head p{color:var(--muted); font-size:14px; margin:0; letter-spacing:.04em}
.crumb{font-size:12px; color:var(--muted); letter-spacing:.06em; padding:16px 0 0}
.crumb a{text-decoration:none}
.crumb a:hover{color:var(--gold)}
/* 下層では節の見出しを重ねて出さない（ページ見出しと二重になる） */
.sub .sec-head{display:none}
.sub section{padding:44px 0 86px}
/* トップの各節に付ける「詳しく見る」 */
.more{text-align:center; margin-top:40px}

/* ---- 過去のお知らせ ---- */
.nlist{padding:52px 0 86px}
.nitem{display:grid; grid-template-columns:140px 1fr; gap:34px;
  padding:32px 0; border-bottom:1px solid var(--line)}
.nitem:first-child{border-top:1px solid var(--line)}
.nitem time{font-family:var(--serif); color:var(--gold-d); font-size:15px;
  letter-spacing:.08em; font-variant-numeric:tabular-nums; padding-top:2px}
.nbody p{margin:0 0 10px; font-size:14.5px; letter-spacing:.02em}
.nbody p:first-child{font-family:var(--serif); font-weight:400; font-size:17px;
  letter-spacing:.08em; line-height:1.8; margin-bottom:14px}
.nbody p:last-child{margin-bottom:0}
.ngal{display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
  gap:12px; margin-top:18px}
.ngal img{width:100%; height:170px; object-fit:cover}

/* ---- 会社概要の表 ---- */
.outline{width:100%; border-collapse:collapse; margin-top:56px; font-size:14px}
.outline th,.outline td{text-align:left; padding:16px 18px; border-bottom:1px solid var(--line);
  vertical-align:top; letter-spacing:.02em}
.outline th{width:190px; font-family:var(--serif); font-weight:400; color:var(--gold-d);
  letter-spacing:.1em; white-space:nowrap}

/* ---- グループの事業 ---- */
.gcards{display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:18px}
.gcard{background:#fff; border:1px solid var(--line); padding:22px 24px}
.gcard h3{font-size:16.5px; margin:0 0 6px}
.gcard .gtag{font-size:11.5px; color:var(--gold,#b39861); margin-bottom:8px; letter-spacing:.06em}
.gcard p{font-size:13.5px; color:var(--muted); margin:0; line-height:1.9}

/* ---- お問い合わせ ---- */
.contact-grid{display:grid; grid-template-columns:1fr 1fr; gap:48px; margin-top:20px}
.contact-box{border:1px solid var(--line); padding:34px 32px}
.contact-box h3{font-family:var(--serif); font-weight:400; font-size:18px;
  letter-spacing:.12em; margin:0 0 14px}
.contact-box .big{font-family:var(--serif); font-size:29px; letter-spacing:.06em; line-height:1.4}
/* メールアドレスは1語なので、狭い幅では折り返せず箱からはみ出す（390pxで
   scrollW 421 になった）。長い語を折り返させ、字送りも詰める。 */
.contact-box .big.mail{font-size:21px; letter-spacing:.02em; overflow-wrap:anywhere; word-break:break-all}
.contact-box p{font-size:13.5px; color:var(--muted); margin:8px 0 0}
.plain{font-size:14px; letter-spacing:.02em}

@media (max-width:760px){
  .nitem{grid-template-columns:1fr; gap:10px; padding:24px 0}
  .nlist{padding:32px 0 56px}
  .outline th{width:auto; display:block; border-bottom:none; padding-bottom:0}
  .outline td{display:block; padding-top:4px}
  .contact-grid{grid-template-columns:1fr; gap:26px}
  .sub section{padding:28px 0 56px}
}
"""


def parts(src_name):
    """原本を、使い回す部品に切り分ける。"""
    s = (SRC / src_name).read_text(encoding="utf-8")
    head = s[: s.index("</head>")]
    head = head.replace("</style>", EXTRA_CSS + "</style>")
    header = s[s.index('<div class="utility">'): s.index('<div class="hero">')]
    hero = s[s.index('<div class="hero">'): s.index('<section id="visas">')]
    cta = s[s.index('<div class="cta" id="contact">'): s.index("<footer>")]
    footer = s[s.index("<footer>"): s.index('<div class="note">')]
    note = s[s.index('<div class="note">'):]
    secs = {}
    for m in re.finditer(r'<section[^>]*id="(\w+)".*?</section>\s*', s, re.S):
        secs[m.group(1)] = m.group(0)
    return head, header, hero, cta, footer, note, secs


def nav_html(current):
    """メニュー。いま見ているページには印を付ける。"""
    def col(items):
        out = []
        for href, label in items:
            on = ' class="on"' if href == current else ""
            out.append(f'<a href="{href}"{on}>{label}</a>')
        return '<nav class="gnav">' + "".join(out) + "</nav>"
    return col(NAV_L), col(NAV_R)


def fix_links(frag, current=None):
    """原本のアンカー（#visas など）をページへの参照に張り替える。
    画像は a/ b/ の1階層下から参照するので ../ を前置する。"""
    for sec, out in ANCHOR.items():
        frag = frag.replace(f'href="#{sec}"', f'href="{out}"')
    frag = frag.replace('src="img/', 'src="../img/')
    return frag


def shell(head, header, footer_html, body, current, title):
    h = re.sub(r"<title>.*?</title>",
               f"<title>{html.escape(title)}｜株式会社 A and K</title>", head, count=1, flags=re.S)
    l, r = nav_html(current)
    hdr = re.sub(r'<nav class="gnav">.*?</nav>', "\x00", header, count=2, flags=re.S)
    hdr = hdr.replace("\x00", l, 1).replace("\x00", r, 1)
    return h + "</head>\n<body>\n\n" + fix_links(hdr) + body + footer_html


def main():
    for key, (src_name, tagline) in PLANS.items():
        out_dir = ROOT / key
        out_dir.mkdir(exist_ok=True)
        build_plan(out_dir, src_name)
        print(f"  {key}/ ← {src_name}  （{tagline}）")
    write_chooser()
    print("  index.html（案の入口）")


def build_plan(out_dir, src_name):
    """1案ぶんの全ページを作る。**ページ構成は案で変えない。**"""
    head, header, hero, cta, footer, note, secs = parts(src_name)
    tail = fix_links(cta) + fix_links(footer) + note

    body = fix_links(hero)
    for out, (sec, _menu, _t, _en, _d) in PAGES.items():
        frag = fix_links(secs[sec])
        frag = frag.replace("</div>\n</section>",
                            f'<div class="more"><a class="btn-more" href="{out}"><span>詳しく見る</span></a></div>\n</div>\n</section>')
        body += frag
    (out_dir / "index.html").write_text(
        shell(head, header, tail, body, "index.html", "外国人材の受入れ支援"), encoding="utf-8")

    for out, (sec, _menu, ttl, en, desc) in PAGES.items():
        ph = (f'<div class="crumb"><div class="wrap"><a href="index.html">ホーム</a> ／ {html.escape(ttl)}</div></div>\n'
              f'<div class="page-head"><div class="wrap"><span class="en">{html.escape(en)}</span>'
              f'<h1>{html.escape(ttl)}</h1><p>{html.escape(desc)}</p></div></div>\n')
        extra = (outline_table() + group_section()) if out == "company.html" else ""
        (out_dir / out).write_text(
            shell(head, header, tail, '<div class="sub">' + ph + fix_links(secs[sec]) + extra + "</div>",
                  out, ttl), encoding="utf-8")

    (out_dir / "news.html").write_text(
        shell(head, header, tail, news_body(), "news.html", "過去のお知らせ"), encoding="utf-8")
    (out_dir / "contact.html").write_text(
        shell(head, header, tail, contact_body(), "contact.html", "お問い合わせ"), encoding="utf-8")
    (out_dir / "privacy.html").write_text(
        shell(head, header, tail, privacy_body(), "privacy.html", "プライバシーポリシー"), encoding="utf-8")


def write_chooser():
    """案の入口。提案書からはここではなく各案の index を直接指す想定だが、
    URLを短く言えるように置いておく。"""
    cards = "".join(
        f'<a class="c" href="{k}/"><b>案{k.upper()}</b><span>{t}</span></a>'
        for k, (_s, t) in PLANS.items())
    (ROOT / "index.html").write_text(f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive">
<title>デザイン案｜株式会社 A and K</title>
<style>
body{{margin:0;background:#f6f8fa;color:#1f2733;
  font-family:-apple-system,BlinkMacSystemFont,"Yu Gothic",Meiryo,sans-serif;
  display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}}
.box{{max-width:640px;width:100%}}
h1{{font-size:19px;font-weight:800;margin:0 0 6px}}
p{{color:#6b7683;font-size:14px;margin:0 0 24px}}
.c{{display:flex;align-items:baseline;gap:16px;background:#fff;border:1px solid #dde4ea;
  padding:22px 24px;margin-bottom:12px;text-decoration:none;color:inherit}}
.c:hover{{border-color:#14a0dc}}
.c b{{font-size:19px;flex:none}}
.c span{{color:#6b7683;font-size:14px}}
</style></head><body><div class="box">
<h1>株式会社 A and K さま トップページ デザイン案</h1>
<p>ページ構成はどちらの案も同じです。見た目だけが違います。</p>
{cards}
</div></body></html>""", encoding="utf-8")


def group_section():
    """グループの事業。旧サイトの h1 と事業内容に、児童福祉の記載があった。
    このサイトは外国人材に絞る方針だが、**落とすのではなく紹介にとどめ、
    詳細はそれぞれのサイトへ渡す**（原則リニューアルをベースにするため）。"""
    cards = [
        ("かみのて保育園", "こども家庭庁所管 企業主導型保育事業",
         "2022年7月開園。外国にルーツのあるお子さまをお預かりしています。",
         "https://www.kaminote-hoikuen.com/"),
        ("かみのて今渡保育園", "可児市 小規模認可保育園",
         "2023年10月開園。可児市の待機児童の解消と、地域の子育て支援に取り組んでいます。", None),
        ("かみのてKIDS・かみのてSMILE", "児童発達支援・放課後等デイサービス",
         "2025年6月にかみのてKIDSが新築移転し、受け入れ人数を増やしました。", None),
        ("一時預かり事業", "",
         "新社屋の2階で、一時預かりも行っています。", None),
    ]
    items = ""
    for name, tag, desc, url in cards:
        link = (f'<p style="margin-top:8px"><a href="{url}" target="_blank" rel="noopener">'
                f'サイトを見る</a></p>' if url else "")
        items += (f'<div class="gcard"><h3>{name}</h3>'
                  f'{f"<div class=\"gtag\">{tag}</div>" if tag else ""}'
                  f'<p>{desc}</p>{link}</div>')
    return ('<section class="alt"><div class="wrap">'
            '<div class="sec-head" style="display:block"><span class="en">GROUP</span>'
            '<h2>グループの事業</h2>'
            '<p>外国人材の受入れ支援のほか、保育園と児童発達支援・放課後等デイサービスを運営しています。</p></div>'
            f'<div class="gcards">{items}</div></div></section>')


def outline_table():
    """会社概要。旧サイトの会社案内ページの内容をそのまま引き継ぐ。"""
    rows = [
        ("会社名", "株式会社 A and K"),
        ("本社所在地", "〒509-0207 岐阜県可児市今渡3-11<br>Tel 0574-66-3511／Fax 0574-66-7311"),
        ("可児今渡事務所", "〒509-0207 岐阜県可児市今渡1149-1 2F<br>Tel・Fax 0574-50-5048"),
        ("代表者", "代表取締役　兼松 厚志"),
        ("E-mail", '<a href="mailto:info@aandkcorp.com">info@aandkcorp.com</a>'),
        ("営業時間", "9:00〜18:00"),
        ("定休日", "土曜日、日曜日"),
        ("許可", "登録支援機関 登録番号 19登-000975"),
        ("事業内容", "・技能実習生の紹介及び手続き代行業務<br>・外国人留学生の紹介業務<br>"
                     "・特定技能登録支援機関<br>・外国籍児童の保育園経営<br>"
                     "・内閣府所管企業主導型保育園経営<br>・認可保育園経営<br>"
                     "・児童発達支援事業・放課後デイサービス事業"),
        ("取引銀行", "岐阜商工信用組合 可児支店<br>十六銀行 西可児支店<br>東濃信用金庫 西可児支店"),
        ("顧問", "高橋法律事務所<br>各務税理士事務所<br>NAKA社会保険労務士事務所"),
    ]
    tr = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    return ('<section><div class="wrap"><div class="sec-head" style="display:block">'
            '<span class="en">OUTLINE</span><h2>会社概要</h2></div>'
            f'<table class="outline">{tr}</table></div></section>')


def news_body():
    items = json.loads((SRC / "news.json").read_text(encoding="utf-8"))
    arts = []
    for it in items:
        body = "".join(f"<p>{html.escape(l)}</p>" for l in ([it["title"]] + it["body"]) if l)
        gal = ""
        if it["images"]:
            gal = '<div class="ngal">' + "".join(
                f'<img src="../img/news/{n}" alt="" loading="lazy">' for n in it["images"]) + "</div>"
        arts.append(f'      <article class="nitem"><time>{it["date"]}</time>'
                    f'<div class="nbody">{body}{gal}</div></article>')
    return ('<div class="crumb"><div class="wrap"><a href="index.html">ホーム</a> ／ 過去のお知らせ</div></div>\n'
            '<div class="page-head"><div class="wrap"><span class="en">NEWS &amp; TOPICS</span>'
            '<h1>過去のお知らせ</h1></div></div>\n'
            '<div class="nlist"><div class="wrap">\n' + "\n".join(arts) + "\n</div></div>\n")


def contact_body():
    return ('<div class="crumb"><div class="wrap"><a href="index.html">ホーム</a> ／ お問い合わせ</div></div>\n'
            '<div class="page-head"><div class="wrap"><span class="en">CONTACT</span>'
            '<h1>お問い合わせ</h1><p>ご相談・お見積りは無料です。制度の説明だけでも承ります。</p></div></div>\n'
            '<section><div class="wrap"><div class="contact-grid">'
            '<div class="contact-box"><h3>お電話でのお問い合わせ</h3>'
            '<div class="big">0574-66-3511</div>'
            '<p>平日 9:00〜18:00（土曜日・日曜日を除く）</p></div>'
            '<div class="contact-box"><h3>メールでのお問い合わせ</h3>'
            '<div class="big mail"><a href="mailto:info@aandkcorp.com" style="text-decoration:none">info@aandkcorp.com</a></div>'
            '<p>お問い合わせフォームは公開時にご用意します。<br>'
            '職種・ご希望の人数・時期をお書き添えいただけると、ご案内がスムーズです。</p></div>'
            '</div></div></section>\n')


def privacy_body():
    return ('<div class="crumb"><div class="wrap"><a href="index.html">ホーム</a> ／ プライバシーポリシー</div></div>\n'
            '<div class="page-head"><div class="wrap"><span class="en">PRIVACY POLICY</span>'
            '<h1>プライバシーポリシー</h1></div></div>\n'
            '<section><div class="wrap"><p class="plain">'
            '現在のホームページに掲載されているプライバシーポリシーの本文を、そのまま引き継ぎます。'
            '（この見本では枠だけご用意しています。）</p></div></section>\n')


if __name__ == "__main__":
    main()
