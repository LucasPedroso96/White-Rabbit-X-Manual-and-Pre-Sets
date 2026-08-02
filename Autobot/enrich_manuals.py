# -*- coding: utf-8 -*-
"""Alinha o pacote de manuais multi-idioma do White Rabbit X.

O que este script faz nos 11 idiomas:

1. Insere a secao de COMUNIDADE na descricao de venda e no FAQ, apontando o
   canal oficial no Telegram, de onde saem os sets prontos e os manuais no
   idioma do comprador.

2. Inclui o aviso anti-golpe junto do convite. Isso nao e enfeite: vendedores
   estabelecidos do MQL5 Market publicam esse aviso porque golpistas abrem
   canais de Telegram falsos vendendo sets "oficiais". Convidar para o canal
   sem dizer qual e o canal verdadeiro cria exatamente a brecha que eles usam.

3. Sincroniza a versao da EA citada nos rodapes.

4. Traduz o cabecalho do CSV de referencia de inputs, que estava em ingles em
   nove dos onze idiomas.

Todo texto novo e escrito no idioma do arquivo. Nada de ingles enfiado numa
pagina em japones.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lucas Pedroso\OneDrive\SantoGral\Santo Gral"
            r"\venda mql5\Pacote_Completo_White_Rabbit_X\Languages")

TELEGRAM = "https://t.me/MrRabbit_MT5"
EA_VERSION = "1.12"

# (titulo, paragrafo de convite, bullets, aviso anti-golpe)
COMMUNITY = {
    "00_Portuguese_Brazil": (
        "Comunidade e downloads",
        f"Entre no canal oficial no Telegram: **{TELEGRAM}**",
        ["Sets prontos por ativo e por tipo de sistema (SL/TP, trailing, grid, "
         "martingale e outros), organizados para carregar direto no Strategy "
         "Tester.",
         "Manuais no seu idioma: portugues, ingles, russo, chines, espanhol, "
         "japones, alemao, coreano, frances, italiano e turco.",
         "Avisos de atualizacao da EA e das bibliotecas de sets.",
         "Suporte e troca de experiencia com outros usuarios."],
        "Este e o unico canal oficial. Nao compre sets ou copias da EA de "
        "terceiros que digam representar o White Rabbit X: a EA e vendida "
        "apenas no MQL5 Market e os sets sao distribuidos gratuitamente no "
        "canal acima."),
    "01_English": (
        "Community and downloads",
        f"Join the official Telegram channel: **{TELEGRAM}**",
        ["Ready-made sets per symbol and per system type (SL/TP, trailing, "
         "grid, martingale and others), organized to load straight into the "
         "Strategy Tester.",
         "Manuals in your language: Portuguese, English, Russian, Chinese, "
         "Spanish, Japanese, German, Korean, French, Italian and Turkish.",
         "Update notices for the EA and for the set libraries.",
         "Support and shared experience with other users."],
        "This is the only official channel. Do not buy sets or copies of the "
        "EA from third parties claiming to represent White Rabbit X: the EA is "
        "sold only on the MQL5 Market and the sets are distributed free of "
        "charge on the channel above."),
    "02_Russian": (
        "Сообщество и загрузки",
        f"Присоединяйтесь к официальному каналу в Telegram: **{TELEGRAM}**",
        ["Готовые наборы параметров по инструментам и типам систем (SL/TP, "
         "трейлинг, сетка, мартингейл и другие), готовые к загрузке в "
         "тестер стратегий.",
         "Руководства на вашем языке: португальский, английский, русский, "
         "китайский, испанский, японский, немецкий, корейский, французский, "
         "итальянский и турецкий.",
         "Уведомления об обновлениях советника и библиотек наборов.",
         "Поддержка и обмен опытом с другими пользователями."],
        "Это единственный официальный канал. Не покупайте наборы или копии "
        "советника у третьих лиц, утверждающих, что они представляют White "
        "Rabbit X: советник продаётся только на MQL5 Market, а наборы "
        "бесплатно распространяются на канале выше."),
    "03_Chinese": (
        "社区与下载",
        f"加入官方 Telegram 频道：**{TELEGRAM}**",
        ["按品种和系统类型（止损止盈、追踪止损、网格、马丁格尔等）分类的现成参数集，"
         "可直接载入策略测试器。",
         "您所用语言的手册：葡萄牙语、英语、俄语、中文、西班牙语、日语、德语、"
         "韩语、法语、意大利语和土耳其语。",
         "EA 与参数集库的更新通知。",
         "技术支持以及与其他用户的经验交流。"],
        "这是唯一的官方频道。请勿从声称代表 White Rabbit X 的第三方购买参数集或 EA "
        "副本：本 EA 仅在 MQL5 Market 销售，参数集在上述频道免费发布。"),
    "04_Spanish": (
        "Comunidad y descargas",
        f"Únase al canal oficial de Telegram: **{TELEGRAM}**",
        ["Sets listos por activo y por tipo de sistema (SL/TP, trailing, "
         "grid, martingala y otros), organizados para cargar directamente en "
         "el Probador de Estrategias.",
         "Manuales en su idioma: portugués, inglés, ruso, chino, español, "
         "japonés, alemán, coreano, francés, italiano y turco.",
         "Avisos de actualización del EA y de las bibliotecas de sets.",
         "Soporte e intercambio de experiencia con otros usuarios."],
        "Este es el único canal oficial. No compre sets ni copias del EA a "
        "terceros que digan representar a White Rabbit X: el EA se vende "
        "únicamente en el MQL5 Market y los sets se distribuyen gratuitamente "
        "en el canal indicado."),
    "05_Japanese": (
        "コミュニティとダウンロード",
        f"公式 Telegram チャンネルにご参加ください：**{TELEGRAM}**",
        ["銘柄別・システム種別（SL/TP、トレーリング、グリッド、マーチンゲールなど）"
         "に整理された既成のセットファイル。ストラテジーテスターにそのまま読み込めます。",
         "お使いの言語のマニュアル：ポルトガル語、英語、ロシア語、中国語、"
         "スペイン語、日本語、ドイツ語、韓国語、フランス語、イタリア語、トルコ語。",
         "EA とセットライブラリの更新通知。",
         "サポートと他のユーザーとの情報交換。"],
        "公式チャンネルはここだけです。White Rabbit X の代理を名乗る第三者から"
        "セットや EA のコピーを購入しないでください。本 EA は MQL5 Market "
        "でのみ販売され、セットは上記チャンネルで無償配布されています。"),
    "06_German": (
        "Community und Downloads",
        f"Treten Sie dem offiziellen Telegram-Kanal bei: **{TELEGRAM}**",
        ["Fertige Sets pro Symbol und pro Systemtyp (SL/TP, Trailing, Grid, "
         "Martingale und weitere), so aufbereitet, dass sie direkt in den "
         "Strategietester geladen werden können.",
         "Handbücher in Ihrer Sprache: Portugiesisch, Englisch, Russisch, "
         "Chinesisch, Spanisch, Japanisch, Deutsch, Koreanisch, Französisch, "
         "Italienisch und Türkisch.",
         "Update-Hinweise zum EA und zu den Set-Bibliotheken.",
         "Support und Erfahrungsaustausch mit anderen Nutzern."],
        "Dies ist der einzige offizielle Kanal. Kaufen Sie keine Sets oder "
        "Kopien des EA von Dritten, die vorgeben, White Rabbit X zu "
        "vertreten: Der EA wird ausschließlich im MQL5 Market verkauft und "
        "die Sets werden im oben genannten Kanal kostenlos verteilt."),
    "07_Korean": (
        "커뮤니티 및 다운로드",
        f"공식 텔레그램 채널에 참여하세요: **{TELEGRAM}**",
        ["종목별·시스템 유형별(SL/TP, 트레일링, 그리드, 마틴게일 등)로 정리된 "
         "완성 세트 파일. 전략 테스터에 바로 불러올 수 있습니다.",
         "사용 언어별 매뉴얼: 포르투갈어, 영어, 러시아어, 중국어, 스페인어, "
         "일본어, 독일어, 한국어, 프랑스어, 이탈리아어, 터키어.",
         "EA 및 세트 라이브러리 업데이트 공지.",
         "지원 및 다른 사용자와의 경험 공유."],
        "공식 채널은 이곳뿐입니다. White Rabbit X를 대리한다고 주장하는 "
        "제3자에게서 세트나 EA 사본을 구매하지 마십시오. 본 EA는 MQL5 "
        "Market에서만 판매되며 세트는 위 채널에서 무료로 배포됩니다."),
    "08_French": (
        "Communauté et téléchargements",
        f"Rejoignez le canal Telegram officiel : **{TELEGRAM}**",
        ["Sets prêts à l'emploi par actif et par type de système (SL/TP, "
         "trailing, grille, martingale et autres), organisés pour être "
         "chargés directement dans le Testeur de Stratégies.",
         "Manuels dans votre langue : portugais, anglais, russe, chinois, "
         "espagnol, japonais, allemand, coréen, français, italien et turc.",
         "Avis de mise à jour de l'EA et des bibliothèques de sets.",
         "Support et échange d'expérience avec les autres utilisateurs."],
        "C'est le seul canal officiel. N'achetez pas de sets ni de copies de "
        "l'EA auprès de tiers prétendant représenter White Rabbit X : l'EA "
        "est vendu uniquement sur le MQL5 Market et les sets sont distribués "
        "gratuitement sur le canal ci-dessus."),
    "09_Italian": (
        "Community e download",
        f"Entra nel canale Telegram ufficiale: **{TELEGRAM}**",
        ["Set pronti per strumento e per tipo di sistema (SL/TP, trailing, "
         "griglia, martingala e altri), organizzati per essere caricati "
         "direttamente nello Strategy Tester.",
         "Manuali nella tua lingua: portoghese, inglese, russo, cinese, "
         "spagnolo, giapponese, tedesco, coreano, francese, italiano e turco.",
         "Avvisi di aggiornamento dell'EA e delle librerie di set.",
         "Supporto e scambio di esperienze con altri utenti."],
        "Questo è l'unico canale ufficiale. Non acquistare set o copie "
        "dell'EA da terzi che dichiarano di rappresentare White Rabbit X: "
        "l'EA è venduto solo sul MQL5 Market e i set sono distribuiti "
        "gratuitamente sul canale indicato."),
    "10_Turkish": (
        "Topluluk ve indirmeler",
        f"Resmî Telegram kanalına katılın: **{TELEGRAM}**",
        ["Enstrümana ve sistem türüne göre (SL/TP, trailing, grid, martingale "
         "ve diğerleri) hazırlanmış set dosyaları; doğrudan Strateji Test "
         "Cihazına yüklenecek şekilde düzenlenmiştir.",
         "Kendi dilinizde kılavuzlar: Portekizce, İngilizce, Rusça, Çince, "
         "İspanyolca, Japonca, Almanca, Korece, Fransızca, İtalyanca ve "
         "Türkçe.",
         "EA ve set kütüphaneleri için güncelleme duyuruları.",
         "Destek ve diğer kullanıcılarla deneyim paylaşımı."],
        "Bu tek resmî kanaldır. White Rabbit X'i temsil ettiğini iddia eden "
        "üçüncü kişilerden set veya EA kopyası satın almayın: EA yalnızca "
        "MQL5 Market üzerinden satılır ve setler yukarıdaki kanalda ücretsiz "
        "dağıtılır."),
}

# Cabecalho do CSV de referencia de inputs, por idioma.
CSV_HEADERS = {
    "01_English": None,  # ja esta correto
    "00_Portuguese_Brazil": None,
    "02_Russian": ["№", "Раздел", "Подраздел", "Параметр", "Тип",
                   "По умолчанию", "Описание", "Варианты перечисления",
                   "Примечания", "EA_Version", "EA_SHA256"],
    "03_Chinese": ["序号", "分区", "子分区", "参数", "类型", "默认值", "说明",
                   "枚举选项", "操作说明", "EA_Version", "EA_SHA256"],
    "04_Spanish": ["N.º", "Sección", "Subsección", "Parámetro", "Tipo",
                   "Predeterminado", "Descripción", "Opciones del enum",
                   "Notas operativas", "EA_Version", "EA_SHA256"],
    "05_Japanese": ["番号", "セクション", "サブセクション", "パラメータ", "型",
                    "既定値", "説明", "列挙オプション", "運用上の注意",
                    "EA_Version", "EA_SHA256"],
    "06_German": ["Nr.", "Abschnitt", "Unterabschnitt", "Parameter", "Typ",
                  "Standard", "Beschreibung", "Enum-Optionen",
                  "Betriebshinweise", "EA_Version", "EA_SHA256"],
    "07_Korean": ["번호", "섹션", "하위 섹션", "매개변수", "형식", "기본값",
                  "설명", "열거형 옵션", "운영 참고", "EA_Version", "EA_SHA256"],
    "08_French": ["N°", "Section", "Sous-section", "Paramètre", "Type",
                  "Par défaut", "Description", "Options d'énumération",
                  "Notes opérationnelles", "EA_Version", "EA_SHA256"],
    "09_Italian": ["N.", "Sezione", "Sottosezione", "Parametro", "Tipo",
                   "Predefinito", "Descrizione", "Opzioni enum",
                   "Note operative", "EA_Version", "EA_SHA256"],
    "10_Turkish": ["No", "Bölüm", "Alt bölüm", "Parametre", "Tür",
                   "Varsayılan", "Açıklama", "Enum seçenekleri",
                   "Operasyonel notlar", "EA_Version", "EA_SHA256"],
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8-sig")


def community_block(lang: str) -> str:
    title, invite, bullets, warning = COMMUNITY[lang]
    lines = [f"## {title}", "", invite, ""]
    lines += [f"- {b}" for b in bullets]
    lines += ["", f"> {warning}", ""]
    return "\n".join(lines)


def insert_community(path: Path, lang: str) -> bool:
    body = read(path)
    title = COMMUNITY[lang][0]
    if f"## {title}" in body or TELEGRAM in body:
        return False
    block = community_block(lang)
    # Entra antes do aviso de risco, que e sempre a ultima secao; se nao
    # houver, vai antes do rodape de versao, e no fim como ultimo recurso.
    sections = list(re.finditer(r"^## .+$", body, re.MULTILINE))
    if sections:
        last = sections[-1]
        body = body[:last.start()] + block + "\n" + body[last.start():]
    else:
        body = body.rstrip() + "\n\n" + block
    write(path, body)
    return True


def sync_version(path: Path) -> bool:
    body = read(path)
    new = re.sub(r"(EA[ _]version:?\s*`?)1\.11(`?)", rf"\g<1>{EA_VERSION}\g<2>",
                 body, flags=re.IGNORECASE)
    new = new.replace("`1.11`", f"`{EA_VERSION}`")
    if new == body:
        return False
    write(path, new)
    return True


def translate_csv_header(path: Path, lang: str) -> bool:
    header = CSV_HEADERS.get(lang)
    if not header:
        return False
    rows = read(path).splitlines()
    if not rows:
        return False
    if rows[0] == ";".join(header):
        return False
    rows[0] = ";".join(header)
    write(path, "\n".join(rows) + "\n")
    return True


def main() -> int:
    touched = {"comunidade": 0, "versao": 0, "csv": 0}
    for lang in sorted(COMMUNITY):
        folder = ROOT / lang
        if not folder.is_dir():
            print(f"AUSENTE: {lang}")
            continue
        for path in sorted(folder.glob("*")):
            if path.is_dir():
                continue
            slot = path.name[:2]
            if path.suffix.lower() == ".md":
                if slot in ("02", "04") and insert_community(path, lang):
                    touched["comunidade"] += 1
                if sync_version(path):
                    touched["versao"] += 1
            elif path.suffix.lower() == ".csv" and slot == "06":
                if translate_csv_header(path, lang):
                    touched["csv"] += 1
            elif path.suffix.lower() == ".txt" and slot == "05":
                body = read(path)
                if TELEGRAM not in body:
                    title, invite, bullets, warning = COMMUNITY[lang]
                    plain = (f"\n\n{title.upper()}\n"
                             + invite.replace("**", "") + "\n"
                             + "\n".join(f"- {b}" for b in bullets)
                             + f"\n\n{warning}\n")
                    write(path, body.rstrip() + plain)
                    touched["comunidade"] += 1

    print(f"Secao de comunidade inserida em {touched['comunidade']} arquivos")
    print(f"Versao sincronizada para {EA_VERSION} em {touched['versao']} arquivos")
    print(f"Cabecalho do CSV traduzido em {touched['csv']} idiomas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
