// ---------------------------------------------------------------- utilidades

const i18n = {
  en: {
    'badge.mt5': 'MT5: ',
    'badge.campaign': 'Campaign: ',
    'install.button': 'Install app',
    'lang.label': 'Language',
    'nav.live': 'Live campaign',
    'nav.setup': 'Run setup',
    'nav.sets': 'Set library',
    'nav.portfolios': 'Portfolios',
    'nav.broker': 'Broker profile',
    'nav.native-cost': 'Native cost',
    'campaign.robustness': 'Robustness diagnosis',
    'campaign.asset-map': 'Asset map by class',
    'campaign.progress': 'Progress by system',
    'campaign.reports': 'Reports and status',
    'campaign.stop-run': 'Stop run',
    'campaign.by-system': 'By system',
    'campaign.recent-combos': 'Latest combos',
    'table.system': 'System',
    'table.tests': 'Tested',
    'table.approved': 'Approved',
    'table.symbol': 'Symbol',
    'table.variant': 'Variant',
    'table.verdict': 'Verdict',
    'table.retention': 'Retention',
    'table.minutes': 'Min',
    'setup.mode': 'Mode',
    'setup.auto': 'Automatic (auto-detect eligible assets)',
    'setup.manual': 'Manual (choose system and asset)',
    'setup.systems': 'Systems',
    'setup.assets': 'Assets',
    'setup.detect': 'Detect available now',
    'setup.parameters': 'Parameters',
    'setup.from': 'From',
    'setup.to': 'To',
    'setup.deposit': 'Deposit',
    'setup.min-retention': 'Minimum retention %',
    'setup.start-run': 'Start run',
    'library.current': 'Current library',
    'library.loading': 'loading...',
    'library.regenerate': 'Regenerate the full library',
    'portfolio.general-map': 'General map',
    'portfolio.loading': 'loading...',
    'portfolio.by-system': 'By system',
    'portfolio.note': 'The set mirror only stores the validated .set, not the original .htm report — point below to a folder where you already gathered the set reports you want to compare.',
    'portfolio.generate': 'Generate correlation panel',
    'profile.interests': 'Interests',
    'profile.assets': 'Assets (empty = all; comma separated)',
    'profile.systems': 'Systems (empty = all)',
    'profile.risk': 'Risk',
    'profile.risk-per-trade': 'Risk per trade %',
    'profile.fixed-lot': 'Fixed lot',
    'profile.walk-forward': 'Walk-forward',
    'profile.final-date': 'Final date',
    'profile.dry-run': 'Dry-run (show only what it would do)',
    'profile.apply': 'Apply for real',
    'profile.last-sync': 'Last synchronization',
    'cost.title': 'Measured fees (per lot)',
    'cost.symbol': 'Native symbol',
    'cost.commission': 'Commission/lot',
    'cost.swap': 'Swap/lot',
    'cost.when': 'Measured on',
    'cost.measure-new': 'Measure a new symbol',
    'cost.measure-now': 'Measure now',
  },
  pt: {
    'badge.mt5': 'MT5: ',
    'badge.campaign': 'Campanha: ',
    'install.button': 'Instalar app',
    'lang.label': 'Idioma',
    'nav.live': 'Campanha ao vivo',
    'nav.setup': 'Configurar corrida',
    'nav.sets': 'Biblioteca de Sets',
    'nav.portfolios': 'Portfólios',
    'nav.broker': 'Perfil da corretora',
    'nav.native-cost': 'Custo nativo',
    'campaign.robustness': 'Diagnóstico de robustez',
    'campaign.asset-map': 'Mapa de ativos por classe',
    'campaign.progress': 'Progresso por sistema',
    'campaign.reports': 'Relatórios e status',
    'campaign.stop-run': 'Parar corrida',
    'campaign.by-system': 'Por sistema',
    'campaign.recent-combos': 'Últimas combinações',
    'table.system': 'Sistema',
    'table.tests': 'Testados',
    'table.approved': 'Aprovados',
    'table.symbol': 'Símbolo',
    'table.variant': 'Variante',
    'table.verdict': 'Veredito',
    'table.retention': 'Retenção',
    'table.minutes': 'Min',
    'setup.mode': 'Modo',
    'setup.auto': 'Automático (detecta ativos elegíveis)',
    'setup.manual': 'Manual (escolher sistema e ativo)',
    'setup.systems': 'Sistemas',
    'setup.assets': 'Ativos',
    'setup.detect': 'Detectar disponíveis agora',
    'setup.parameters': 'Parâmetros',
    'setup.from': 'De',
    'setup.to': 'Até',
    'setup.deposit': 'Depósito',
    'setup.min-retention': 'Retenção mínima %',
    'setup.start-run': 'Iniciar corrida',
    'library.current': 'Biblioteca atual',
    'library.loading': 'carregando...',
    'library.regenerate': 'Regenerar a biblioteca completa',
    'portfolio.general-map': 'Mapa geral',
    'portfolio.loading': 'carregando...',
    'portfolio.by-system': 'Por sistema',
    'portfolio.note': 'O espelho de sets guarda só o <code>.set</code> validado, não o relatório <code>.htm</code> original — aponte abaixo para uma pasta onde você já reuniu os relatórios de sets que quer comparar.',
    'portfolio.generate': 'Gerar painel de correlação',
    'profile.interests': 'Interesses',
    'profile.assets': 'Ativos (vazio = todos; separados por vírgula)',
    'profile.systems': 'Sistemas (vazio = todos)',
    'profile.risk': 'Risco',
    'profile.risk-per-trade': 'Risco por trade %',
    'profile.fixed-lot': 'Lote fixo',
    'profile.walk-forward': 'Walk-forward',
    'profile.final-date': 'Data final',
    'profile.dry-run': 'Dry-run (mostrar só o que faria)',
    'profile.apply': 'Aplicar de verdade',
    'profile.last-sync': 'Última sincronização',
    'cost.title': 'Taxas medidas (por lote)',
    'cost.symbol': 'Símbolo nativo',
    'cost.commission': 'Comissão/lote',
    'cost.swap': 'Swap/lote',
    'cost.when': 'Medido em',
    'cost.measure-new': 'Medir um novo símbolo',
    'cost.measure-now': 'Medir agora',
  },
  es: {
    'badge.mt5': 'MT5: ',
    'badge.campaign': 'Campaña: ',
    'install.button': 'Instalar app',
    'lang.label': 'Idioma',
    'nav.live': 'Campaña en vivo',
    'nav.setup': 'Configurar corrida',
    'nav.sets': 'Biblioteca de sets',
    'nav.portfolios': 'Portafolios',
    'nav.broker': 'Perfil del bróker',
    'nav.native-cost': 'Costo nativo',
    'campaign.robustness': 'Diagnóstico de robustez',
    'campaign.asset-map': 'Mapa de activos por clase',
    'campaign.progress': 'Progreso por sistema',
    'campaign.reports': 'Informes y estado',
    'campaign.stop-run': 'Detener corrida',
    'campaign.by-system': 'Por sistema',
    'campaign.recent-combos': 'Últimas combinaciones',
    'table.system': 'Sistema',
    'table.tests': 'Probados',
    'table.approved': 'Aprobados',
    'table.symbol': 'Símbolo',
    'table.variant': 'Variante',
    'table.verdict': 'Veredicto',
    'table.retention': 'Retención',
    'table.minutes': 'Min',
    'setup.mode': 'Modo',
    'setup.auto': 'Automático (detecta activos elegibles)',
    'setup.manual': 'Manual (elegir sistema y activo)',
    'setup.systems': 'Sistemas',
    'setup.assets': 'Activos',
    'setup.detect': 'Detectar disponibles ahora',
    'setup.parameters': 'Parámetros',
    'setup.from': 'Desde',
    'setup.to': 'Hasta',
    'setup.deposit': 'Depósito',
    'setup.min-retention': 'Retención mínima %',
    'setup.start-run': 'Iniciar corrida',
    'library.current': 'Biblioteca actual',
    'library.loading': 'cargando...',
    'library.regenerate': 'Regenerar la biblioteca completa',
    'portfolio.general-map': 'Mapa general',
    'portfolio.loading': 'cargando...',
    'portfolio.by-system': 'Por sistema',
    'portfolio.note': 'El espejo de sets solo guarda el <code>.set</code> validado, no el informe <code>.htm</code> original — apunte abajo a una carpeta donde ya haya reunido los informes de sets que quiere comparar.',
    'portfolio.generate': 'Generar panel de correlación',
    'profile.interests': 'Intereses',
    'profile.assets': 'Activos (vacío = todos; separados por coma)',
    'profile.systems': 'Sistemas (vacío = todos)',
    'profile.risk': 'Riesgo',
    'profile.risk-per-trade': 'Riesgo por operación %',
    'profile.fixed-lot': 'Lote fijo',
    'profile.walk-forward': 'Walk-forward',
    'profile.final-date': 'Fecha final',
    'profile.dry-run': 'Dry-run (mostrar solo lo que haría)',
    'profile.apply': 'Aplicar de verdad',
    'profile.last-sync': 'Última sincronización',
    'cost.title': 'Comisiones medidas (por lote)',
    'cost.symbol': 'Símbolo nativo',
    'cost.commission': 'Comisión/lote',
    'cost.swap': 'Swap/lote',
    'cost.when': 'Medido el',
    'cost.measure-new': 'Medir un nuevo símbolo',
    'cost.measure-now': 'Medir ahora',
  },
  de: {
    'badge.mt5': 'MT5: ',
    'badge.campaign': 'Kampagne: ',
    'install.button': 'App installieren',
    'lang.label': 'Sprache',
    'nav.live': 'Live-Kampagne',
    'nav.setup': 'Lauf einrichten',
    'nav.sets': 'Set-Bibliothek',
    'nav.portfolios': 'Portfolios',
    'nav.broker': 'Broker-Profil',
    'nav.native-cost': 'Nativkosten',
    'campaign.robustness': 'Robustheitsdiagnose',
    'campaign.asset-map': 'Asset-Karte nach Klasse',
    'campaign.progress': 'Fortschritt nach System',
    'campaign.reports': 'Berichte und Status',
    'campaign.stop-run': 'Lauf stoppen',
    'campaign.by-system': 'Nach System',
    'campaign.recent-combos': 'Neueste Kombinationen',
    'table.system': 'System',
    'table.tests': 'Getestet',
    'table.approved': 'Genehmigt',
    'table.symbol': 'Symbol',
    'table.variant': 'Variante',
    'table.verdict': 'Urteil',
    'table.retention': 'Retention',
    'table.minutes': 'Min',
    'setup.mode': 'Modus',
    'setup.auto': 'Automatisch (erkennt geeignete Assets)',
    'setup.manual': 'Manuell (System und Asset wählen)',
    'setup.systems': 'Systeme',
    'setup.assets': 'Assets',
    'setup.detect': 'Jetzt verfügbare erkennen',
    'setup.parameters': 'Parameter',
    'setup.from': 'Von',
    'setup.to': 'Bis',
    'setup.deposit': 'Einzahlung',
    'setup.min-retention': 'Mindest-Retention %',
    'setup.start-run': 'Lauf starten',
    'library.current': 'Aktuelle Bibliothek',
    'library.loading': 'lädt...',
    'library.regenerate': 'Gesamte Bibliothek neu generieren',
    'portfolio.general-map': 'Gesamtkarte',
    'portfolio.loading': 'lädt...',
    'portfolio.by-system': 'Nach System',
    'portfolio.note': 'Der Set-Spiegel speichert nur das validierte <code>.set</code>, nicht den ursprünglichen <code>.htm</code>-Bericht — verweisen Sie unten auf einen Ordner, in dem Sie die zu vergleichenden Set-Berichte bereits gesammelt haben.',
    'portfolio.generate': 'Korrelationspanel erzeugen',
    'profile.interests': 'Interessen',
    'profile.assets': 'Assets (leer = alle; kommagetrennt)',
    'profile.systems': 'Systeme (leer = alle)',
    'profile.risk': 'Risiko',
    'profile.risk-per-trade': 'Risiko pro Trade %',
    'profile.fixed-lot': 'Fixes Lot',
    'profile.walk-forward': 'Walk-Forward',
    'profile.final-date': 'Enddatum',
    'profile.dry-run': 'Dry-Run (nur anzeigen, was passieren würde)',
    'profile.apply': 'Wirklich anwenden',
    'profile.last-sync': 'Letzte Synchronisierung',
    'cost.title': 'Gemessene Gebühren (pro Lot)',
    'cost.symbol': 'Natives Symbol',
    'cost.commission': 'Kommission/Lot',
    'cost.swap': 'Swap/Lot',
    'cost.when': 'Gemessen am',
    'cost.measure-new': 'Neues Symbol messen',
    'cost.measure-now': 'Jetzt messen',
  },
  fr: {
    'badge.mt5': 'MT5 : ',
    'badge.campaign': 'Campagne : ',
    'install.button': "Installer l'app",
    'lang.label': 'Langue',
    'nav.live': 'Campagne en direct',
    'nav.setup': 'Configurer la campagne',
    'nav.sets': 'Bibliothèque de sets',
    'nav.portfolios': 'Portefeuilles',
    'nav.broker': 'Profil du broker',
    'nav.native-cost': 'Coût natif',
    'campaign.robustness': 'Diagnostic de robustesse',
    'campaign.asset-map': 'Carte des actifs par classe',
    'campaign.progress': 'Progression par système',
    'campaign.reports': 'Rapports et statut',
    'campaign.stop-run': 'Arrêter la campagne',
    'campaign.by-system': 'Par système',
    'campaign.recent-combos': 'Dernières combinaisons',
    'table.system': 'Système',
    'table.tests': 'Testés',
    'table.approved': 'Approuvés',
    'table.symbol': 'Symbole',
    'table.variant': 'Variante',
    'table.verdict': 'Verdict',
    'table.retention': 'Rétention',
    'table.minutes': 'Min',
    'setup.mode': 'Mode',
    'setup.auto': 'Automatique (détecte les actifs éligibles)',
    'setup.manual': 'Manuel (choisir système et actif)',
    'setup.systems': 'Systèmes',
    'setup.assets': 'Actifs',
    'setup.detect': 'Détecter les actifs disponibles',
    'setup.parameters': 'Paramètres',
    'setup.from': 'De',
    'setup.to': 'À',
    'setup.deposit': 'Dépôt',
    'setup.min-retention': 'Rétention minimale %',
    'setup.start-run': 'Démarrer la campagne',
    'library.current': 'Bibliothèque actuelle',
    'library.loading': 'chargement...',
    'library.regenerate': 'Régénérer la bibliothèque complète',
    'portfolio.general-map': 'Carte générale',
    'portfolio.loading': 'chargement...',
    'portfolio.by-system': 'Par système',
    'portfolio.note': "Le miroir de sets ne conserve que le <code>.set</code> validé, pas le rapport <code>.htm</code> d'origine — indiquez ci-dessous un dossier où vous avez déjà rassemblé les rapports de sets à comparer.",
    'portfolio.generate': 'Générer le panneau de corrélation',
    'profile.interests': 'Intérêts',
    'profile.assets': 'Actifs (vide = tous ; séparés par des virgules)',
    'profile.systems': 'Systèmes (vide = tous)',
    'profile.risk': 'Risque',
    'profile.risk-per-trade': 'Risque par trade %',
    'profile.fixed-lot': 'Lot fixe',
    'profile.walk-forward': 'Walk-forward',
    'profile.final-date': 'Date finale',
    'profile.dry-run': 'Dry-run (afficher seulement ce qui serait fait)',
    'profile.apply': 'Appliquer pour de vrai',
    'profile.last-sync': 'Dernière synchronisation',
    'cost.title': 'Frais mesurés (par lot)',
    'cost.symbol': 'Symbole natif',
    'cost.commission': 'Commission/lot',
    'cost.swap': 'Swap/lot',
    'cost.when': 'Mesuré le',
    'cost.measure-new': 'Mesurer un nouveau symbole',
    'cost.measure-now': 'Mesurer maintenant',
  },
  it: {
    'badge.mt5': 'MT5: ',
    'badge.campaign': 'Campagna: ',
    'install.button': "Installa l'app",
    'lang.label': 'Lingua',
    'nav.live': 'Campagna live',
    'nav.setup': 'Configura run',
    'nav.sets': 'Libreria set',
    'nav.portfolios': 'Portafogli',
    'nav.broker': 'Profilo broker',
    'nav.native-cost': 'Costo nativo',
    'campaign.robustness': 'Diagnosi di robustezza',
    'campaign.asset-map': 'Mappa asset per classe',
    'campaign.progress': 'Avanzamento per sistema',
    'campaign.reports': 'Report e stato',
    'campaign.stop-run': 'Ferma run',
    'campaign.by-system': 'Per sistema',
    'campaign.recent-combos': 'Ultime combinazioni',
    'table.system': 'Sistema',
    'table.tests': 'Testati',
    'table.approved': 'Approvati',
    'table.symbol': 'Simbolo',
    'table.variant': 'Variante',
    'table.verdict': 'Verdetto',
    'table.retention': 'Retention',
    'table.minutes': 'Min',
    'setup.mode': 'Modalità',
    'setup.auto': 'Automatica (rileva asset idonei)',
    'setup.manual': 'Manuale (scegli sistema e asset)',
    'setup.systems': 'Sistemi',
    'setup.assets': 'Asset',
    'setup.detect': 'Rileva disponibili ora',
    'setup.parameters': 'Parametri',
    'setup.from': 'Da',
    'setup.to': 'A',
    'setup.deposit': 'Deposito',
    'setup.min-retention': 'Retention minima %',
    'setup.start-run': 'Avvia run',
    'library.current': 'Libreria attuale',
    'library.loading': 'caricamento...',
    'library.regenerate': "Rigenerare l'intera libreria",
    'portfolio.general-map': 'Mappa generale',
    'portfolio.loading': 'caricamento...',
    'portfolio.by-system': 'Per sistema',
    'portfolio.note': 'Lo specchio dei set conserva solo il <code>.set</code> validato, non il report <code>.htm</code> originale — indica sotto una cartella dove hai già raccolto i report dei set da confrontare.',
    'portfolio.generate': 'Genera pannello di correlazione',
    'profile.interests': 'Interessi',
    'profile.assets': 'Asset (vuoto = tutti; separati da virgola)',
    'profile.systems': 'Sistemi (vuoto = tutti)',
    'profile.risk': 'Rischio',
    'profile.risk-per-trade': 'Rischio per trade %',
    'profile.fixed-lot': 'Lotto fisso',
    'profile.walk-forward': 'Walk-forward',
    'profile.final-date': 'Data finale',
    'profile.dry-run': 'Dry-run (mostra solo cosa farebbe)',
    'profile.apply': 'Applica davvero',
    'profile.last-sync': 'Ultima sincronizzazione',
    'cost.title': 'Costi misurati (per lotto)',
    'cost.symbol': 'Simbolo nativo',
    'cost.commission': 'Commissione/lotto',
    'cost.swap': 'Swap/lotto',
    'cost.when': 'Misurato il',
    'cost.measure-new': 'Misura un nuovo simbolo',
    'cost.measure-now': 'Misura ora',
  },
  ru: {
    'badge.mt5': 'MT5: ',
    'badge.campaign': 'Кампания: ',
    'install.button': 'Установить приложение',
    'lang.label': 'Язык',
    'nav.live': 'Кампания в реальном времени',
    'nav.setup': 'Настройка прогона',
    'nav.sets': 'Библиотека сетов',
    'nav.portfolios': 'Портфели',
    'nav.broker': 'Профиль брокера',
    'nav.native-cost': 'Нативные издержки',
    'campaign.robustness': 'Диагностика устойчивости',
    'campaign.asset-map': 'Карта активов по классам',
    'campaign.progress': 'Прогресс по системам',
    'campaign.reports': 'Отчёты и статус',
    'campaign.stop-run': 'Остановить прогон',
    'campaign.by-system': 'По системам',
    'campaign.recent-combos': 'Последние комбинации',
    'table.system': 'Система',
    'table.tests': 'Протестировано',
    'table.approved': 'Одобрено',
    'table.symbol': 'Символ',
    'table.variant': 'Вариант',
    'table.verdict': 'Вердикт',
    'table.retention': 'Retention',
    'table.minutes': 'Мин',
    'setup.mode': 'Режим',
    'setup.auto': 'Автоматический (определяет подходящие активы)',
    'setup.manual': 'Ручной (выбрать систему и актив)',
    'setup.systems': 'Системы',
    'setup.assets': 'Активы',
    'setup.detect': 'Определить доступные сейчас',
    'setup.parameters': 'Параметры',
    'setup.from': 'С',
    'setup.to': 'По',
    'setup.deposit': 'Депозит',
    'setup.min-retention': 'Минимальный retention %',
    'setup.start-run': 'Запустить прогон',
    'library.current': 'Текущая библиотека',
    'library.loading': 'загрузка...',
    'library.regenerate': 'Перегенерировать всю библиотеку',
    'portfolio.general-map': 'Общая карта',
    'portfolio.loading': 'загрузка...',
    'portfolio.by-system': 'По системам',
    'portfolio.note': 'Зеркало сетов хранит только проверенный <code>.set</code>, а не исходный отчёт <code>.htm</code> — укажите ниже папку, где вы уже собрали отчёты по сетам для сравнения.',
    'portfolio.generate': 'Сформировать панель корреляции',
    'profile.interests': 'Интересы',
    'profile.assets': 'Активы (пусто = все; через запятую)',
    'profile.systems': 'Системы (пусто = все)',
    'profile.risk': 'Риск',
    'profile.risk-per-trade': 'Риск на сделку %',
    'profile.fixed-lot': 'Фиксированный лот',
    'profile.walk-forward': 'Walk-forward',
    'profile.final-date': 'Конечная дата',
    'profile.dry-run': 'Dry-run (показать только, что будет сделано)',
    'profile.apply': 'Применить по-настоящему',
    'profile.last-sync': 'Последняя синхронизация',
    'cost.title': 'Измеренные издержки (за лот)',
    'cost.symbol': 'Нативный символ',
    'cost.commission': 'Комиссия/лот',
    'cost.swap': 'Своп/лот',
    'cost.when': 'Измерено',
    'cost.measure-new': 'Измерить новый символ',
    'cost.measure-now': 'Измерить сейчас',
  },
  zh: {
    'badge.mt5': 'MT5：',
    'badge.campaign': '活动：',
    'install.button': '安装应用',
    'lang.label': '语言',
    'nav.live': '实时活动',
    'nav.setup': '配置运行',
    'nav.sets': '参数集库',
    'nav.portfolios': '投资组合',
    'nav.broker': '经纪商配置',
    'nav.native-cost': '原生成本',
    'campaign.robustness': '稳健性诊断',
    'campaign.asset-map': '按类别划分的资产地图',
    'campaign.progress': '按系统划分的进度',
    'campaign.reports': '报告与状态',
    'campaign.stop-run': '停止运行',
    'campaign.by-system': '按系统',
    'campaign.recent-combos': '最新组合',
    'table.system': '系统',
    'table.tests': '已测试',
    'table.approved': '已批准',
    'table.symbol': '品种',
    'table.variant': '变体',
    'table.verdict': '结论',
    'table.retention': '留存率',
    'table.minutes': '分钟',
    'setup.mode': '模式',
    'setup.auto': '自动（自动检测符合条件的资产）',
    'setup.manual': '手动（选择系统和资产）',
    'setup.systems': '系统',
    'setup.assets': '资产',
    'setup.detect': '检测当前可用项',
    'setup.parameters': '参数',
    'setup.from': '起始',
    'setup.to': '结束',
    'setup.deposit': '入金',
    'setup.min-retention': '最低留存率 %',
    'setup.start-run': '开始运行',
    'library.current': '当前库',
    'library.loading': '加载中...',
    'library.regenerate': '重新生成完整库',
    'portfolio.general-map': '总览地图',
    'portfolio.loading': '加载中...',
    'portfolio.by-system': '按系统',
    'portfolio.note': '参数集镜像只保存已验证的 <code>.set</code> 文件，不保存原始的 <code>.htm</code> 报告——请在下方指定一个已收集好待比较参数集报告的文件夹。',
    'portfolio.generate': '生成相关性面板',
    'profile.interests': '关注项',
    'profile.assets': '资产（留空 = 全部；用逗号分隔）',
    'profile.systems': '系统（留空 = 全部）',
    'profile.risk': '风险',
    'profile.risk-per-trade': '每笔交易风险 %',
    'profile.fixed-lot': '固定手数',
    'profile.walk-forward': 'Walk-forward',
    'profile.final-date': '结束日期',
    'profile.dry-run': '演练模式（仅显示将执行的操作）',
    'profile.apply': '真实应用',
    'profile.last-sync': '上次同步',
    'cost.title': '实测费用（每手）',
    'cost.symbol': '原生品种',
    'cost.commission': '佣金/手',
    'cost.swap': '隔夜利息/手',
    'cost.when': '测量时间',
    'cost.measure-new': '测量新品种',
    'cost.measure-now': '立即测量',
  },
  ja: {
    'badge.mt5': 'MT5: ',
    'badge.campaign': 'キャンペーン: ',
    'install.button': 'アプリをインストール',
    'lang.label': '言語',
    'nav.live': 'ライブキャンペーン',
    'nav.setup': '実行設定',
    'nav.sets': 'セットライブラリ',
    'nav.portfolios': 'ポートフォリオ',
    'nav.broker': 'ブローカープロファイル',
    'nav.native-cost': 'ネイティブコスト',
    'campaign.robustness': 'ロバストネス診断',
    'campaign.asset-map': 'クラス別アセットマップ',
    'campaign.progress': 'システム別進捗',
    'campaign.reports': 'レポートとステータス',
    'campaign.stop-run': '実行を停止',
    'campaign.by-system': 'システム別',
    'campaign.recent-combos': '最新の組み合わせ',
    'table.system': 'システム',
    'table.tests': 'テスト済み',
    'table.approved': '承認済み',
    'table.symbol': 'シンボル',
    'table.variant': 'バリアント',
    'table.verdict': '判定',
    'table.retention': 'リテンション',
    'table.minutes': '分',
    'setup.mode': 'モード',
    'setup.auto': '自動（対象アセットを自動検出）',
    'setup.manual': '手動（システムとアセットを選択）',
    'setup.systems': 'システム',
    'setup.assets': 'アセット',
    'setup.detect': '現在利用可能なものを検出',
    'setup.parameters': 'パラメータ',
    'setup.from': '開始',
    'setup.to': '終了',
    'setup.deposit': '入金額',
    'setup.min-retention': '最小リテンション %',
    'setup.start-run': '実行を開始',
    'library.current': '現在のライブラリ',
    'library.loading': '読み込み中...',
    'library.regenerate': 'ライブラリ全体を再生成',
    'portfolio.general-map': '全体マップ',
    'portfolio.loading': '読み込み中...',
    'portfolio.by-system': 'システム別',
    'portfolio.note': 'セットミラーは検証済みの <code>.set</code> のみを保存し、元の <code>.htm</code> レポートは保存しません — 比較したいセットレポートを既に集めてあるフォルダを下で指定してください。',
    'portfolio.generate': '相関パネルを生成',
    'profile.interests': '関心対象',
    'profile.assets': 'アセット（空欄=すべて、カンマ区切り）',
    'profile.systems': 'システム（空欄=すべて）',
    'profile.risk': 'リスク',
    'profile.risk-per-trade': 'トレードごとのリスク %',
    'profile.fixed-lot': '固定ロット',
    'profile.walk-forward': 'ウォークフォワード',
    'profile.final-date': '終了日',
    'profile.dry-run': 'ドライラン（実行内容の表示のみ）',
    'profile.apply': '実際に適用',
    'profile.last-sync': '最終同期',
    'cost.title': '実測手数料（ロットあたり）',
    'cost.symbol': 'ネイティブシンボル',
    'cost.commission': '手数料/ロット',
    'cost.swap': 'スワップ/ロット',
    'cost.when': '測定日時',
    'cost.measure-new': '新しいシンボルを測定',
    'cost.measure-now': '今すぐ測定',
  },
  ko: {
    'badge.mt5': 'MT5: ',
    'badge.campaign': '캠페인: ',
    'install.button': '앱 설치',
    'lang.label': '언어',
    'nav.live': '실시간 캠페인',
    'nav.setup': '실행 설정',
    'nav.sets': '세트 라이브러리',
    'nav.portfolios': '포트폴리오',
    'nav.broker': '브로커 프로필',
    'nav.native-cost': '네이티브 비용',
    'campaign.robustness': '강건성 진단',
    'campaign.asset-map': '자산군별 자산 맵',
    'campaign.progress': '시스템별 진행 상황',
    'campaign.reports': '보고서 및 상태',
    'campaign.stop-run': '실행 중지',
    'campaign.by-system': '시스템별',
    'campaign.recent-combos': '최신 조합',
    'table.system': '시스템',
    'table.tests': '테스트됨',
    'table.approved': '승인됨',
    'table.symbol': '심볼',
    'table.variant': '변형',
    'table.verdict': '판정',
    'table.retention': '리텐션',
    'table.minutes': '분',
    'setup.mode': '모드',
    'setup.auto': '자동 (적격 자산 자동 감지)',
    'setup.manual': '수동 (시스템과 자산 선택)',
    'setup.systems': '시스템',
    'setup.assets': '자산',
    'setup.detect': '현재 사용 가능한 항목 감지',
    'setup.parameters': '파라미터',
    'setup.from': '시작일',
    'setup.to': '종료일',
    'setup.deposit': '입금액',
    'setup.min-retention': '최소 리텐션 %',
    'setup.start-run': '실행 시작',
    'library.current': '현재 라이브러리',
    'library.loading': '로딩 중...',
    'library.regenerate': '전체 라이브러리 재생성',
    'portfolio.general-map': '전체 맵',
    'portfolio.loading': '로딩 중...',
    'portfolio.by-system': '시스템별',
    'portfolio.note': '세트 미러는 검증된 <code>.set</code>만 저장하며 원본 <code>.htm</code> 리포트는 저장하지 않습니다 — 비교하려는 세트 리포트를 이미 모아둔 폴더를 아래에서 지정하세요.',
    'portfolio.generate': '상관관계 패널 생성',
    'profile.interests': '관심 항목',
    'profile.assets': '자산 (비워두면 전체; 쉼표로 구분)',
    'profile.systems': '시스템 (비워두면 전체)',
    'profile.risk': '리스크',
    'profile.risk-per-trade': '거래당 리스크 %',
    'profile.fixed-lot': '고정 로트',
    'profile.walk-forward': '워크포워드',
    'profile.final-date': '종료 날짜',
    'profile.dry-run': '드라이런 (실행될 내용만 표시)',
    'profile.apply': '실제로 적용',
    'profile.last-sync': '마지막 동기화',
    'cost.title': '측정된 수수료 (로트당)',
    'cost.symbol': '네이티브 심볼',
    'cost.commission': '수수료/로트',
    'cost.swap': '스왑/로트',
    'cost.when': '측정 시점',
    'cost.measure-new': '새 심볼 측정',
    'cost.measure-now': '지금 측정',
  },
  tr: {
    'badge.mt5': 'MT5: ',
    'badge.campaign': 'Kampanya: ',
    'install.button': 'Uygulamayı yükle',
    'lang.label': 'Dil',
    'nav.live': 'Canlı kampanya',
    'nav.setup': 'Çalıştırma ayarları',
    'nav.sets': 'Set kütüphanesi',
    'nav.portfolios': 'Portföyler',
    'nav.broker': 'Broker profili',
    'nav.native-cost': 'Native maliyet',
    'campaign.robustness': 'Sağlamlık tanısı',
    'campaign.asset-map': 'Sınıfa göre varlık haritası',
    'campaign.progress': 'Sisteme göre ilerleme',
    'campaign.reports': 'Raporlar ve durum',
    'campaign.stop-run': 'Çalıştırmayı durdur',
    'campaign.by-system': 'Sisteme göre',
    'campaign.recent-combos': 'Son kombinasyonlar',
    'table.system': 'Sistem',
    'table.tests': 'Test edildi',
    'table.approved': 'Onaylandı',
    'table.symbol': 'Sembol',
    'table.variant': 'Varyant',
    'table.verdict': 'Sonuç',
    'table.retention': 'Retention',
    'table.minutes': 'Dk',
    'setup.mode': 'Mod',
    'setup.auto': 'Otomatik (uygun varlıkları otomatik algılar)',
    'setup.manual': 'Manuel (sistem ve varlık seç)',
    'setup.systems': 'Sistemler',
    'setup.assets': 'Varlıklar',
    'setup.detect': 'Şu an müsait olanları algıla',
    'setup.parameters': 'Parametreler',
    'setup.from': 'Başlangıç',
    'setup.to': 'Bitiş',
    'setup.deposit': 'Depozito',
    'setup.min-retention': 'Minimum retention %',
    'setup.start-run': 'Çalıştırmayı başlat',
    'library.current': 'Mevcut kütüphane',
    'library.loading': 'yükleniyor...',
    'library.regenerate': 'Tüm kütüphaneyi yeniden oluştur',
    'portfolio.general-map': 'Genel harita',
    'portfolio.loading': 'yükleniyor...',
    'portfolio.by-system': 'Sisteme göre',
    'portfolio.note': 'Set aynası yalnızca doğrulanmış <code>.set</code> dosyasını saklar, orijinal <code>.htm</code> raporunu saklamaz — aşağıda karşılaştırmak istediğiniz set raporlarını zaten topladığınız bir klasörü belirtin.',
    'portfolio.generate': 'Korelasyon panelini oluştur',
    'profile.interests': 'İlgi alanları',
    'profile.assets': 'Varlıklar (boş = tümü; virgülle ayrılmış)',
    'profile.systems': 'Sistemler (boş = tümü)',
    'profile.risk': 'Risk',
    'profile.risk-per-trade': 'İşlem başına risk %',
    'profile.fixed-lot': 'Sabit lot',
    'profile.walk-forward': 'Walk-forward',
    'profile.final-date': 'Bitiş tarihi',
    'profile.dry-run': 'Dry-run (yalnızca ne yapılacağını göster)',
    'profile.apply': 'Gerçekten uygula',
    'profile.last-sync': 'Son senkronizasyon',
    'cost.title': 'Ölçülen ücretler (lot başına)',
    'cost.symbol': 'Native sembol',
    'cost.commission': 'Komisyon/lot',
    'cost.swap': 'Swap/lot',
    'cost.when': 'Ölçüm tarihi',
    'cost.measure-new': 'Yeni sembol ölç',
    'cost.measure-now': 'Şimdi ölç',
  }
};

const langPicker = document.getElementById('lang-picker');

function applyTranslations(locale = 'en') {
  const data = i18n[locale] || i18n.en;
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.dataset.i18n;
    if (data[key]) el.textContent = data[key];
  });
}

langPicker?.addEventListener('change', (event) => {
  applyTranslations(event.target.value);
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}

let deferredInstallPrompt = null;
const installButton = document.getElementById("btn-install");

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  deferredInstallPrompt = event;
  installButton.style.display = "inline-flex";
});

installButton.addEventListener("click", async () => {
  if (!deferredInstallPrompt) {
    installButton.textContent = "Prompt indisponível no navegador";
    return;
  }
  deferredInstallPrompt.prompt();
  await deferredInstallPrompt.userChoice;
  deferredInstallPrompt = null;
  installButton.style.display = "none";
});

async function api(path, opts) {
  const r = await fetch(path, opts);
  return r.json();
}
async function post(path, body) {
  return api(path, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
}

async function pollJob(jobId, msgEl, onDone) {
  msgEl.textContent = "rodando...";
  msgEl.className = "status-msg";
  const tick = async () => {
    const j = await api(`/api/jobs/${jobId}`);
    if (j.status === "rodando" || j.status === "iniciado") {
      setTimeout(tick, 2000);
      return;
    }
    if (j.status === "feito") {
      msgEl.textContent = "concluído.";
      msgEl.className = "status-msg ok";
    } else {
      msgEl.textContent = "erro: " + (j.saida || "").slice(-300);
      msgEl.className = "status-msg no";
    }
    onDone && onDone(j);
  };
  tick();
}

// ------------------------------------------------------------------- abas

document.querySelectorAll("nav button[data-tab]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("nav button[data-tab]").forEach((b) => b.classList.remove("ativo"));
    document.querySelectorAll(".painel").forEach((p) => p.classList.remove("ativo"));
    btn.classList.add("ativo");
    document.getElementById("painel-" + btn.dataset.tab).classList.add("ativo");
    if (btn.dataset.tab === "biblioteca") carregarBiblioteca();
    if (btn.dataset.tab === "portfolios") carregarPortfolios();
    if (btn.dataset.tab === "custo") carregarCusto();
    if (btn.dataset.tab === "implantacao") carregarImplantacao();
  });
});

// ---------------------------------------------------------- campanha ao vivo

// Linhas de detalhe expandidas pelo usuario -- sobrevivem ao refresh de 8s
// (que reconstroi #tbl-recentes do zero) porque o clique so muda este Set,
// nao o DOM direto; o proximo carregarStatus() reaplica o estado.
const linhasExpandidas = new Set();
document.querySelector("#tbl-recentes").addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-chave]");
  if (!btn) return;
  const chave = btn.dataset.chave;
  if (linhasExpandidas.has(chave)) linhasExpandidas.delete(chave);
  else linhasExpandidas.add(chave);
  const idLinha = "det-" + chave.replace(/[^a-zA-Z0-9]/g, "_");
  document.getElementById(idLinha)?.classList.toggle("linha-oculta");
});

async function carregarStatus() {
  const d = await api("/api/status");
  const q = d.qualidade || {};
  const emAndamento = d.atual ? 1 : 0;
  const mcMedido = q.mc_pass_rate != null;
  const mcPct = Number(q.mc_pass_rate ?? 0);
  const ret = Number(q.retencao_media ?? 0);
  const narrativa = !mcMedido
    ? "no Monte Carlo measurement yet (fine for grid/martingale/d'Alembert, which are structurally exempt) — judge by retention alone for now"
    : mcPct >= 70 && ret >= 70
    ? "robust: the majority of the ledger already shows MC and out-of-sample retention aligned"
    : mcPct >= 40
      ? "mixed: evidence is acceptable, but there is still robustness noise to clean up"
      : "fragile: the dashboard still does not show enough robustness to run without filtering";
  document.getElementById("cards").innerHTML = `
    <div class="card">Done<b>${d.total_feitos}</b></div>
    <div class="card">Approved<b class="ok">${d.aprovados}</b></div>
    <div class="card">Rejected<b class="no">${d.reprovados}</b></div>
    <div class="card">In progress<b class="live">${emAndamento}</b></div>`;
  const a = d.atual;
  document.getElementById("atual").innerHTML = a
    ? `<b class="live">RUNNING NOW</b> [${a.posicao}] ${a.simbolo} ${a.sistema} ${a.variante}<br>
       <span style="color:#9aa">${a.estagio || "..."}</span>`
    : `<span style="color:#9aa">No active combo at the moment.</span>`;
  document.querySelector("#tbl-sistemas tbody").innerHTML =
    Object.entries(d.por_sistema).map(([s, v]) =>
      `<tr><td>${s}</td><td>${v.total}</td><td>${v.aprovados}</td></tr>`).join("");
  document.getElementById("sistema-bars").innerHTML = Object.entries(d.por_sistema).map(([s, v]) => {
    const pct = v.total ? Math.round((v.aprovados / v.total) * 100) : 0;
    const tone = pct >= 70 ? "ok" : pct >= 40 ? "live" : "no";
    return `<div class="bar-item"><div class="bar-label"><span>${s}</span><span>${v.aprovados}/${v.total}</span></div>
      <div class="progress-track"><div class="progress-fill ${tone}" style="width:${pct}%"></div></div>
      <div class="bar-note">${pct}% approved</div></div>`;
  }).join("") || `<span class="status-msg">no validated system yet</span>`;
  document.getElementById("quality-grid").innerHTML = `
    <div class="metric-card"><div class="metric-label">MC pass rate</div><b>${mcMedido ? q.mc_pass_rate + "%" : "n/d"}</b>
      <div class="metric-label" style="margin-top:4px">${q.mc_medidos ?? 0} of ${d.total_feitos} measured (${q.mc_cobertura_pct ?? 0}%)</div></div>
    <div class="metric-card"><div class="metric-label">Average retention</div><b>${q.retencao_media ?? "-"}%</b></div>
    <div class="metric-card"><div class="metric-label">Average real tick profit</div><b>${q.lucro_medio_tick_real ?? "-"}</b></div>
    <div class="metric-card"><div class="metric-label">Status</div><b>${narrativa}</b></div>`;
  document.getElementById("quality-summary").innerHTML = `
    <span class="status-msg">MC: ${q.mc_status}</span><br>
    <span class="status-msg">WFE: ${q.wfe_status}</span><br>
    <span class="status-msg ok">Summary: ${narrativa}</span>`;
  document.getElementById("wfe-mc-panel").innerHTML = `
    <div class="diagnostic-row"><span>MC approved in ledger</span><strong>${mcMedido ? q.mc_pass_rate + "%" : "n/d (" + (q.mc_medidos ?? 0) + " measured)"}</strong></div>
    <div class="diagnostic-row"><span>Average OOS retention</span><strong>${q.retencao_media ?? "-"}%</strong></div>
    <div class="diagnostic-row"><span>Average real tick profit</span><strong>${q.lucro_medio_tick_real ?? "-"}</strong></div>
    <div class="diagnostic-row"><span>Interpretation</span><strong>${narrativa}</strong></div>`;
  document.querySelector("#tbl-recentes tbody").innerHTML = d.recentes.map((r) => {
    // Chave estavel por linha do ledger (nao por indice): o intervalo de 8s
    // reconstroi a tabela inteira, e um id por indice perderia o "expandido"
    // do usuario a cada refresh -- achado testando isso ao vivo.
    const chaveLinha = `${r.simbolo}|${r.sistema}|${r.variante}|${r.quando}`;
    const idLinha = "det-" + chaveLinha.replace(/[^a-zA-Z0-9]/g, "_");
    const ok = r.aprovado;
    const linhaPrincipal = `<tr class="${ok ? "ok" : "no"}"><td>${r.simbolo}</td><td>${r.sistema}</td>
      <td>${r.variante}</td><td><span class="pill ${ok ? "ok" : "no"}">${ok ? "approved" : "rejected"}</span></td>
      <td>${r.retencao_oos ?? "-"}</td>
      <td>${r.expectancy_r != null ? r.expectancy_r.toFixed(3) + "R" : "-"}</td>
      <td>${r.trades_oos ?? (r.trades_is != null ? "~" + r.trades_is + " (IS)" : "-")}</td>
      <td>${r.minutos ?? "-"}</td>
      <td><button class="acao secundario" style="padding:2px 8px;font-size:11px"
          data-chave="${chaveLinha}">···</button></td></tr>`;
    const mc = (r.mc_dd_p95 != null || r.mc_dd_observado != null || r.mc_prob_ruina != null)
      ? `MC: DD p95 ${r.mc_dd_p95 ?? "-"} | DD observado ${r.mc_dd_observado ?? "-"} | prob. ruína ${
          r.mc_prob_ruina != null ? (r.mc_prob_ruina * 100).toFixed(1) + "%" : "-"}`
      : "MC: não medido (fora de Fixed-R ou poucos trades)";
    const oculta = linhasExpandidas.has(chaveLinha) ? "" : "linha-oculta";
    const linhaDetalhe = `<tr id="${idLinha}" class="linha-detalhe ${oculta}"><td colspan="9">
      <div class="detalhe-grid">
        <span>lucro OHLC/busca: <b>${r.lucro_ohlc ?? "-"}</b></span>
        <span>lucro tick real: <b>${r.lucro_tick_real ?? "-"}</b></span>
        <span>lucro ajustado (custo nativo): <b>${r.lucro_ajustado_custo_nativo ?? "n/d"}</b></span>
        <span>retenção %: <b>${r.retencao_pct ?? "-"}</b></span>
        <span>sizing entregue: <b>${r.sizing_entrega ?? "-"}</b></span>
        <span>${mc}</span>
        ${r.relatorio_dir ? `<span><a href="/relatorios/${r.relatorio_dir}/conf_wrx.htm" target="_blank">relatório completo ↗</a></span>` : ""}
      </div></td></tr>`;
    return linhaPrincipal + linhaDetalhe;
  }).join("");
}

async function carregarEstado() {
  const e = await api("/api/campanha/estado");
  const badgeMt5 = document.getElementById("badge-mt5");
  badgeMt5.textContent = "MT5: " + (e.terminal_aberto ? "busy" : "free");
  badgeMt5.style.background = e.terminal_aberto ? "#3a1b1b" : "#14532d";
  const badgeC = document.getElementById("badge-campanha");
  badgeC.textContent = "Campaign: " + (e.rodando ? "running (" + (e.modo || "?") + ")" : "stopped");
  badgeC.style.background = e.rodando ? "#14532d" : "#243047";
  document.getElementById("btn-stop").disabled = !e.rodando;
  document.getElementById("btn-iniciar").disabled = e.rodando;
}

document.getElementById("btn-stop").addEventListener("click", async () => {
  const msg = document.getElementById("msg-stop");
  msg.textContent = "stopping...";
  const r = await post("/api/campanha/stop");
  msg.textContent = r.ok
    ? `stopped. terminal closed: ${r.terminal_fechado}. incomplete entries removed: ${r.entradas_incompletas_removidas}`
    : "stop error";
  msg.className = "status-msg " + (r.ok ? "ok" : "no");
  carregarEstado();
});

// Preenche os campos de data final com HOJE, calculado no carregamento --
// um valor cravado no HTML fica velho silenciosamente (achado ao vivo,
// 2026-08-03: campo esquecido em 2026.07.21 fez o EURUSD grid rodar contra
// uma janela 13 dias mais curta do que devia, sem nenhum aviso).
function hojeMT5() {
  const d = new Date();
  const dois = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}.${dois(d.getMonth() + 1)}.${dois(d.getDate())}`;
}
document.getElementById("campo-fim").value = hojeMT5();
document.getElementById("perfil-wfo-fim").value = hojeMT5();

setInterval(() => { carregarStatus(); carregarEstado(); carregarHeatmap(); }, 8000);
applyTranslations(langPicker?.value || 'en');
carregarStatus();
carregarEstado();

// ------------------------------------------------------------ configurar corrida

let modoAtual = "auto";
let CONFIG = null;

document.getElementById("btn-modo-auto").addEventListener("click", () => setModo("auto"));
document.getElementById("btn-modo-manual").addEventListener("click", () => setModo("manual"));
function setModo(m) {
  modoAtual = m;
  document.getElementById("btn-modo-auto").classList.toggle("ativo", m === "auto");
  document.getElementById("btn-modo-manual").classList.toggle("ativo", m === "manual");
  document.getElementById("bloco-manual").style.display = m === "manual" ? "block" : "none";
}

async function carregarConfig() {
  CONFIG = await api("/api/config");
  document.getElementById("check-sistemas").innerHTML = CONFIG.sistemas.map((s, i) =>
    `<label><input type="checkbox" value="${s.code}" ${i < 2 ? "checked" : ""}> ${s.code} — ${s.label}</label>`
  ).join("");
  const grupos = document.getElementById("grupos-ativos");
  grupos.innerHTML = Object.entries(CONFIG.classes).map(([classe, info]) => `
    <fieldset><legend>${classe} (capital base ${info.capital_base})</legend>
    <div class="grid-check">${info.ativos.map((a) =>
      `<label><input type="checkbox" class="chk-ativo" value="${a}"> ${a}</label>`).join("")}</div>
    </fieldset>`).join("");
}
carregarConfig();

// Gradiente continuo por retencao, inspirado no densityClass() do dashboard
// do Historical Tool Manager -- pass/fail sozinho nao diz SE vale a pena,
// so se rodou. sem_teste/reprovado continuam tons fixos (nao ha "retencao"
// nesses dois estados); aprovado ganha 3 faixas conforme a melhor retencao.
function densityClass(c) {
  if (c.status === "sem_teste") return "hm-none";
  if (c.status === "reprovado") return "hm-fail";
  const r = c.melhor_retencao;
  if (r === null || r === undefined) return "hm-pass";
  if (r >= 70) return "hm-high";
  if (r >= 40) return "hm-mid";
  return "hm-low";
}

async function carregarHeatmap() {
  const d = await api("/api/heatmap");
  const el = document.getElementById("ativos-map");
  const nomesClasse = Object.keys(d.classes || {});
  if (!nomesClasse.length) {
    el.innerHTML = `<span class="status-msg">no combo tested yet — the map fills in as the campaign runs.</span>`;
    return;
  }
  el.innerHTML = nomesClasse.map((classe) => {
    const info = d.classes[classe];
    const header = `<th></th>` + d.sistemas.map((sc) => `<th title="${sc}">${sc.slice(0, 2)}</th>`).join("");
    const linhas = info.ativos.map((linha) => {
      const celulas = d.sistemas.map((sc) => {
        const c = linha.celulas[sc] || { status: "sem_teste" };
        const tom = densityClass(c);
        const ret = c.melhor_retencao;
        const dica = c.status === "sem_teste"
          ? `${sc}: not tested`
          : `${sc}: ${c.aprovados}/${c.testados} approved — best retention ${ret != null ? ret + "%" : "n/d"}`;
        return `<td><span class="hm-cell ${tom}" title="${dica}"></span></td>`;
      }).join("");
      return `<tr><th>${linha.simbolo}</th>${celulas}</tr>`;
    }).join("");
    return `<div class="hm-box">
      <div class="hm-class-title">${classe} (${info.ativos.length} tested)</div>
      <div class="hm-scroll"><table class="hm-table"><thead><tr>${header}</tr></thead>
      <tbody>${linhas}</tbody></table></div>
    </div>`;
  }).join("");
}
carregarHeatmap();

document.getElementById("btn-detectar").addEventListener("click", async () => {
  const msg = document.getElementById("msg-detectar");
  const r = await post("/api/ativos/detectar");
  if (!r.ok) { msg.textContent = r.erro; msg.className = "status-msg no"; return; }
  pollJob(r.job_id, msg, (j) => {
    if (j.status !== "feito") return;
    const linha = (j.saida || "").split("\n").find((l) => l.includes("simbolos"));
    if (!linha) return;
    const nomes = (linha.match(/\(([^)]*)\)/) || [, ""])[1].split(",").map((s) => s.trim());
    document.querySelectorAll(".chk-ativo").forEach((c) => {
      // O nome real pode vir com sufixo (EURUSD.HT, EURUSDm...) -- usar esse
      // nome exato, nao o generico da biblioteca, ou o /config: do terminal
      // falha em silencio pra um simbolo que essa conta nao tem (achado
      // 2026-08-06: EURUSD puro em vez de EURUSD.HT -- "sem JSON final" em
      // 12s, nenhum passe rodou de verdade).
      const real = nomes.find((n) => n === c.value || n.startsWith(c.value + "."));
      if (real) {
        c.checked = true;
        c.dataset.real = real;
        const label = c.closest("label");
        if (label && real !== c.value) {
          label.title = `usa ${real} nesta conta`;
          label.classList.add("ativo-resolvido");
        }
      }
    });
  });
});

document.getElementById("btn-iniciar").addEventListener("click", async () => {
  const msg = document.getElementById("msg-iniciar");
  const body = {
    modo: modoAtual,
    inicio: document.getElementById("campo-inicio").value,
    fim: document.getElementById("campo-fim").value,
    deposit: Number(document.getElementById("campo-deposito").value),
    min_retencao: Number(document.getElementById("campo-retencao").value),
  };
  if (modoAtual === "manual") {
    body.sistemas = [...document.querySelectorAll("#check-sistemas input:checked")].map((c) => c.value);
    body.simbolos = [...document.querySelectorAll(".chk-ativo:checked")].map((c) => c.dataset.real || c.value);
  }
  const r = await post("/api/campanha/start", body);
  msg.textContent = r.ok ? `iniciado (pid ${r.pid})` : r.erro;
  msg.className = "status-msg " + (r.ok ? "ok" : "no");
  carregarEstado();
});

// -------------------------------------------------------------- biblioteca

async function carregarBiblioteca() {
  const d = await api("/api/biblioteca");
  const el = document.getElementById("info-biblioteca");
  el.textContent = d.manifesto
    ? `${d.manifesto.total_sets} sets | gerado em ${d.manifesto.gerado_em}`
    : "sem biblioteca gerada ainda";
}
document.getElementById("btn-regenerar").addEventListener("click", async () => {
  const msg = document.getElementById("msg-regenerar");
  const r = await post("/api/biblioteca/regenerar");
  if (!r.ok) { msg.textContent = r.erro; msg.className = "status-msg no"; return; }
  pollJob(r.job_id, msg, () => carregarBiblioteca());
});

// -------------------------------------------------------------- portfolios

let portfolioSistemas = {};
let portfolioSelecionado = null;

function mostrarPortfolioIframe(url) {
  const frame = document.getElementById("portfolio-iframe");
  const msg = document.getElementById("msg-portfolio-iframe");
  frame.src = url;
  frame.style.display = "block";
  msg.style.display = "none";
}

async function carregarPortfolios() {
  const d = await api("/api/portfolios");
  document.getElementById("mapa-html").innerHTML = d.mapa_html || "sem MAPA.md ainda";
  portfolioSistemas = d.sistemas || {};
  const tabs = document.getElementById("tabs-sistemas-portfolio");
  const nomes = Object.keys(portfolioSistemas);
  tabs.innerHTML = nomes.map((n) => `<button data-sis="${n}">${n}</button>`).join("");
  tabs.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => selecionarPortfolio(b.dataset.sis)));
  if (nomes.length) selecionarPortfolio(nomes[0]);

  const gerados = d.gerados || [];
  const tabsGerados = document.getElementById("tabs-portfolio-gerados");
  tabsGerados.innerHTML = gerados.map((g) => `<button data-url="${g.url}">${g.nome}</button>`).join("")
    || `<span class="status-msg">no correlation panel generated yet — pick a folder above.</span>`;
  tabsGerados.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    tabsGerados.querySelectorAll("button").forEach((x) => x.classList.toggle("ativo", x === b));
    mostrarPortfolioIframe(b.dataset.url);
  }));
  if (gerados.length) {
    tabsGerados.querySelector("button")?.classList.add("ativo");
    mostrarPortfolioIframe(gerados[0].url);
  }
}
function selecionarPortfolio(nome) {
  portfolioSelecionado = nome;
  document.querySelectorAll("#tabs-sistemas-portfolio button").forEach((b) =>
    b.classList.toggle("ativo", b.dataset.sis === nome));
  document.getElementById("portfolio-sistema-html").innerHTML = portfolioSistemas[nome] || "";
}
document.getElementById("btn-gerar-portfolio").addEventListener("click", async () => {
  const msg = document.getElementById("msg-portfolio");
  const pasta = document.getElementById("portfolio-pasta").value.trim();
  if (!pasta) { msg.textContent = "informe a pasta com os relatórios"; msg.className = "status-msg no"; return; }
  const r = await post("/api/portfolios/gerar", { pasta, nome: portfolioSelecionado || "geral" });
  if (!r.ok) { msg.textContent = r.erro; msg.className = "status-msg no"; return; }
  pollJob(r.job_id, msg, (j) => {
    if (j.status === "feito") {
      msg.textContent = `concluído: ${r.arquivo}`;
      mostrarPortfolioIframe(r.url);
      carregarPortfolios();
    }
  });
});

// ------------------------------------------------------------------ perfil

async function carregarPerfil() {
  document.getElementById("perfil-sistemas").innerHTML = (CONFIG ? CONFIG.sistemas : []).map((s) =>
    `<label><input type="checkbox" class="chk-perfil-sistema" value="${s.code}"> ${s.code}</label>`).join("");
  const d = await api("/api/perfil");
  document.getElementById("ultima-sync").textContent =
    d.ultima_sincronizacao ? JSON.stringify(d.ultima_sincronizacao, null, 2) : "nenhuma ainda";
}
carregarConfig().then(carregarPerfil);

function montarPerfil() {
  const ativos = document.getElementById("perfil-ativos").value
    .split(",").map((s) => s.trim()).filter(Boolean);
  const sistemas = [...document.querySelectorAll(".chk-perfil-sistema:checked")].map((c) => c.value);
  return {
    interesses: { ativos, sistemas, lados: ["BUY", "SELL"], variantes: ["MULTI", "ICHIMOKU"] },
    risco: {
      risco_por_trade_pct: Number(document.getElementById("perfil-risco").value),
      lote_fixo: Number(document.getElementById("perfil-lote").value),
      usar_lote_minimo_do_broker: true,
    },
    walk_forward: { ligar: false, data_final: document.getElementById("perfil-wfo-fim").value },
    arquivar_fora_do_escopo: false,
  };
}
async function sincronizarPerfil(dryRun) {
  const msg = document.getElementById("msg-perfil");
  const r = await post("/api/perfil/sincronizar", { perfil: montarPerfil(), dry_run: dryRun });
  if (!r.ok) { msg.textContent = r.erro; msg.className = "status-msg no"; return; }
  pollJob(r.job_id, msg, (j) => {
    document.getElementById("saida-perfil").textContent = j.saida || "";
    carregarPerfil();
  });
}
document.getElementById("btn-perfil-dry").addEventListener("click", () => sincronizarPerfil(true));
document.getElementById("btn-perfil-aplicar").addEventListener("click", () => sincronizarPerfil(false));

// -------------------------------------------------------------- custo nativo

async function carregarCusto() {
  const d = await api("/api/custo-nativo");
  document.querySelector("#tbl-custo tbody").innerHTML = Object.entries(d).map(([sym, c]) =>
    `<tr><td>${sym}</td><td>${c.comissao_por_lote.toFixed(4)}</td>
     <td>${c.swap_por_lote.toFixed(4)}</td><td>${c.entradas ?? "-"}</td>
     <td>${c.volume_lotes != null ? c.volume_lotes.toFixed(2) : "-"}</td>
     <td>${c.periodo ?? "-"}</td><td>${c.quando}</td></tr>`).join("");
}
document.getElementById("btn-medir-custo").addEventListener("click", async () => {
  const msg = document.getElementById("msg-custo");
  const simbolo = document.getElementById("custo-simbolo").value.trim();
  if (!simbolo) { msg.textContent = "informe o símbolo"; msg.className = "status-msg no"; return; }
  const r = await post("/api/custo-nativo/medir", { symbol: simbolo });
  if (!r.ok) { msg.textContent = r.erro; msg.className = "status-msg no"; return; }
  pollJob(r.job_id, msg, () => carregarCusto());
});

// -------------------------------------------------------------- implantacao

let implantacaoSets = [];

// Sobrevive ao refresh (mesmo padrao de linhasExpandidas em tbl-recentes):
// a chave e o proprio `chave` do set (simbolo__sistema__variante), ja
// estavel por natureza.
const implantacaoExpandida = new Set();
document.querySelector("#tbl-implantacao").addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-grafico]");
  if (!btn) return;
  const chave = btn.dataset.grafico;
  if (implantacaoExpandida.has(chave)) implantacaoExpandida.delete(chave);
  else implantacaoExpandida.add(chave);
  document.getElementById("graf-" + chave.replace(/[^a-zA-Z0-9]/g, "_"))
    ?.classList.toggle("linha-oculta");
});

async function carregarImplantacao() {
  const d = await api("/api/implantacao");
  implantacaoSets = d.sets || [];
  document.querySelector("#tbl-implantacao tbody").innerHTML = implantacaoSets.map((s) => {
    const lucroCompleto = s.sobrevivencia_medida && s.sobrevivencia_saldo_final != null
      ? s.sobrevivencia_saldo_final.toFixed(2)
      : (s.sobrevivencia_medida ? "n/d" : "not measured (non-grid)");
    const idGraf = "graf-" + s.chave.replace(/[^a-zA-Z0-9]/g, "_");
    const oculta = implantacaoExpandida.has(s.chave) ? "" : "linha-oculta";
    const linhaPrincipal = `
    <tr>
      <td><input type="checkbox" class="chk-implantacao" value="${s.chave}" ${s.certificado ? "" : "disabled"}></td>
      <td>${s.simbolo}</td><td>${s.sistema}</td><td>${s.variante}</td>
      <td>${s.retencao ?? "-"}${s.retencao != null ? "%" : ""}</td>
      <td>${lucroCompleto}</td>
      <td>${s.lucro_oos != null ? s.lucro_oos.toFixed(2) : "-"}</td>
      <td>${s.certificado
        ? `<span class="pill ok">certified</span>`
        : `<span class="pill no">no report archived</span>`}</td>
      <td><label style="display:inline-flex;align-items:center;gap:4px">
        <input type="checkbox" class="chk-deployed" value="${s.chave}" ${s.implantado ? "checked" : ""}
          ${s.certificado ? "" : "disabled"}> deployed</label></td>
      <td>${s.sobrevivencia_grafico
        ? `<button class="acao secundario" style="padding:2px 8px;font-size:11px" data-grafico="${s.chave}">chart</button>`
        : ""}</td>
    </tr>`;
    const linhaGrafico = s.sobrevivencia_grafico ? `
    <tr id="${idGraf}" class="linha-detalhe ${oculta}"><td colspan="10">
      <div class="detalhe-grid">
        <span>Full-period equity curve (the one the survival gate actually measured — not the short OOS window):</span>
        <img src="/relatorios/${s.relatorio_dir}/sobrevivencia.png" style="max-width:100%;border:1px solid var(--line);border-radius:6px;margin-top:4px" alt="Full-period equity curve">
        <span><a href="/relatorios/${s.relatorio_dir}/sobrevivencia.htm" target="_blank">full report ↗</a></span>
      </div></td></tr>` : "";
    return linhaPrincipal + linhaGrafico;
  }).join("")
    || `<tr><td colspan="10" class="status-msg">no validated set yet.</td></tr>`;

  document.querySelectorAll(".chk-deployed").forEach((chk) => {
    chk.addEventListener("change", async () => {
      await post("/api/implantacao/marcar", { chaves: [chk.value], implantado: chk.checked });
    });
  });
}

document.getElementById("btn-implantacao-todos").addEventListener("click", () => {
  document.querySelectorAll(".chk-implantacao:not(:disabled)").forEach((c) => { c.checked = true; });
});
document.getElementById("btn-implantacao-nenhum").addEventListener("click", () => {
  document.querySelectorAll(".chk-implantacao").forEach((c) => { c.checked = false; });
});

document.getElementById("btn-implantacao-exportar").addEventListener("click", async () => {
  const msg = document.getElementById("msg-implantacao");
  const chaves = [...document.querySelectorAll(".chk-implantacao:checked")].map((c) => c.value);
  if (!chaves.length) { msg.textContent = "select at least one certified set"; msg.className = "status-msg no"; return; }
  msg.textContent = "preparing .zip...";
  msg.className = "status-msg";
  const resp = await fetch("/api/implantacao/exportar", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chaves }),
  });
  if (!resp.ok) {
    const erro = await resp.json().catch(() => ({}));
    msg.textContent = erro.erro || "export failed";
    msg.className = "status-msg no";
    return;
  }
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "sets_certificados.zip";
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
  msg.textContent = `exported ${chaves.length} set(s).`;
  msg.className = "status-msg ok";
});
