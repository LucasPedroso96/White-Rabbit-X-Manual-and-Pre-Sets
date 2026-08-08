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
    'nav.implantacao': 'Deployment',
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
    'setup.select-all-systems': 'Select all systems',
    'setup.clear-systems': 'Clear selection',
    'setup.select-all-assets': 'Select all assets',
    'setup.clear-assets': 'Clear selection',
    'setup.parameters': 'Parameters',
    'setup.from': 'From',
    'setup.to': 'To',
    'setup.deposit': 'Deposit',
    'setup.min-retention': 'Minimum retention %',
    'setup.start-run': 'Start run',
    'auto-modal.title': 'What Automatic mode does',
    'auto-modal.p1': 'Automatic mode evolves the training on its own: it tests every real asset detected on this account/terminal, across all 11 systems, in risk order (research systems first, then hedge-account grid, then high-risk recovery systems last). It resumes from where it left off using the existing ledger/cache -- nothing already validated gets redone.',
    'auto-modal.p2': 'This can run continuously for a very long time (a full sweep across every asset and system is realistically weeks to months, not hours). It follows the same risk-tiered methodology described in PLANO_TREINAMENTO_100_A_MILHAO.md.',
    'auto-modal.p3': "If you want to choose exactly which systems and assets run, use Manual mode instead -- nothing is removed, both modes stay available.",
    'auto-modal.dont-ask': "Don't show this again on this browser",
    'auto-modal.confirm': 'Understood, start Automatic',
    'auto-modal.prefer-manual': "I'd rather use Manual mode",
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
    'nav.implantacao': 'Implantação',
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
    'setup.select-all-systems': 'Selecionar todos os sistemas',
    'setup.clear-systems': 'Limpar seleção',
    'setup.select-all-assets': 'Selecionar todos os ativos',
    'setup.clear-assets': 'Limpar seleção',
    'setup.parameters': 'Parâmetros',
    'setup.from': 'De',
    'setup.to': 'Até',
    'setup.deposit': 'Depósito',
    'setup.min-retention': 'Retenção mínima %',
    'setup.start-run': 'Iniciar corrida',
    'auto-modal.title': 'O que o Modo Automático faz',
    'auto-modal.p1': 'O Modo Automático evolui o treinamento sozinho: testa todo ativo real detectado nesta conta/terminal, nos 11 sistemas, em ordem de risco (sistemas de pesquisa primeiro, depois grid de conta com hedging, depois sistemas de recuperação de alto risco por último). Retoma de onde parou usando o ledger/cache existente -- nada já validado é refeito.',
    'auto-modal.p2': 'Isso pode rodar continuamente por muito tempo (uma varredura completa por todos os ativos e sistemas é realisticamente semanas a meses, não horas). Segue a mesma metodologia por tier de risco descrita em PLANO_TREINAMENTO_100_A_MILHAO.md.',
    'auto-modal.p3': 'Se quiser escolher exatamente quais sistemas e ativos rodam, use o Modo Manual -- nada é removido, os dois modos continuam disponíveis.',
    'auto-modal.dont-ask': 'Não mostrar isso de novo neste navegador',
    'auto-modal.confirm': 'Entendi, iniciar Automático',
    'auto-modal.prefer-manual': 'Prefiro usar o Modo Manual',
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
    'nav.implantacao': 'Despliegue',
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
    'setup.select-all-systems': 'Seleccionar todos los sistemas',
    'setup.clear-systems': 'Borrar selección',
    'setup.select-all-assets': 'Seleccionar todos los activos',
    'setup.clear-assets': 'Borrar selección',
    'setup.parameters': 'Parámetros',
    'setup.from': 'Desde',
    'setup.to': 'Hasta',
    'setup.deposit': 'Depósito',
    'setup.min-retention': 'Retención mínima %',
    'setup.start-run': 'Iniciar corrida',
    'auto-modal.title': 'Qué hace el Modo Automático',
    'auto-modal.p1': 'El Modo Automático evoluciona el entrenamiento por sí solo: prueba cada activo real detectado en esta cuenta/terminal, en los 11 sistemas, en orden de riesgo (sistemas de investigación primero, luego grid de cuenta con hedging, luego sistemas de recuperación de alto riesgo al final). Retoma donde quedó usando el ledger/caché existente -- nada ya validado se repite.',
    'auto-modal.p2': 'Esto puede ejecutarse continuamente durante mucho tiempo (un barrido completo por todos los activos y sistemas es realistamente semanas a meses, no horas). Sigue la misma metodología por nivel de riesgo descrita en PLANO_TREINAMENTO_100_A_MILHAO.md.',
    'auto-modal.p3': 'Si quiere elegir exactamente qué sistemas y activos se ejecutan, use el Modo Manual -- nada se elimina, ambos modos siguen disponibles.',
    'auto-modal.dont-ask': 'No mostrar esto de nuevo en este navegador',
    'auto-modal.confirm': 'Entendido, iniciar Automático',
    'auto-modal.prefer-manual': 'Prefiero usar el Modo Manual',
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
    'nav.implantacao': 'Bereitstellung',
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
    'setup.select-all-systems': 'Alle Systeme auswählen',
    'setup.clear-systems': 'Auswahl aufheben',
    'setup.select-all-assets': 'Alle Assets auswählen',
    'setup.clear-assets': 'Auswahl aufheben',
    'setup.parameters': 'Parameter',
    'setup.from': 'Von',
    'setup.to': 'Bis',
    'setup.deposit': 'Einzahlung',
    'setup.min-retention': 'Mindest-Retention %',
    'setup.start-run': 'Lauf starten',
    'auto-modal.title': 'Was der Automatikmodus macht',
    'auto-modal.p1': 'Der Automatikmodus entwickelt das Training selbstständig weiter: er testet jedes real erkannte Asset auf diesem Konto/Terminal, in allen 11 Systemen, in Risikoreihenfolge (Research-Systeme zuerst, dann Hedging-Konto-Grid, dann Hochrisiko-Recovery-Systeme zuletzt). Er setzt dort fort, wo er aufgehört hat, anhand des vorhandenen Ledgers/Caches -- bereits Validiertes wird nicht wiederholt.',
    'auto-modal.p2': 'Das kann sehr lange durchgehend laufen (ein vollständiger Durchlauf über alle Assets und Systeme dauert realistisch Wochen bis Monate, nicht Stunden). Folgt derselben risikogestaffelten Methodik, die in PLANO_TREINAMENTO_100_A_MILHAO.md beschrieben ist.',
    'auto-modal.p3': 'Wenn Sie genau festlegen möchten, welche Systeme und Assets laufen, nutzen Sie stattdessen den manuellen Modus -- nichts wird entfernt, beide Modi bleiben verfügbar.',
    'auto-modal.dont-ask': 'Dies in diesem Browser nicht mehr anzeigen',
    'auto-modal.confirm': 'Verstanden, Automatik starten',
    'auto-modal.prefer-manual': 'Ich bevorzuge den manuellen Modus',
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
    'nav.implantacao': 'Déploiement',
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
    'setup.select-all-systems': 'Sélectionner tous les systèmes',
    'setup.clear-systems': 'Effacer la sélection',
    'setup.select-all-assets': 'Sélectionner tous les actifs',
    'setup.clear-assets': 'Effacer la sélection',
    'setup.parameters': 'Paramètres',
    'setup.from': 'De',
    'setup.to': 'À',
    'setup.deposit': 'Dépôt',
    'setup.min-retention': 'Rétention minimale %',
    'setup.start-run': 'Démarrer la campagne',
    'auto-modal.title': 'Ce que fait le Mode Automatique',
    'auto-modal.p1': "Le Mode Automatique fait évoluer l'entraînement tout seul : il teste chaque actif réel détecté sur ce compte/terminal, sur les 11 systèmes, dans l'ordre de risque (systèmes de recherche d'abord, puis grid à compte de couverture, puis systèmes de récupération à haut risque en dernier). Il reprend là où il s'est arrêté grâce au registre/cache existant -- rien de déjà validé n'est refait.",
    'auto-modal.p2': "Cela peut tourner en continu très longtemps (un balayage complet de tous les actifs et systèmes prend réalistement des semaines à des mois, pas des heures). Suit la même méthodologie par niveau de risque décrite dans PLANO_TREINAMENTO_100_A_MILHAO.md.",
    'auto-modal.p3': "Si vous voulez choisir exactement quels systèmes et actifs sont exécutés, utilisez plutôt le Mode Manuel -- rien n'est supprimé, les deux modes restent disponibles.",
    'auto-modal.dont-ask': 'Ne plus afficher ceci sur ce navigateur',
    'auto-modal.confirm': 'Compris, démarrer Automatique',
    'auto-modal.prefer-manual': 'Je préfère utiliser le Mode Manuel',
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
    'nav.implantacao': 'Distribuzione',
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
    'setup.select-all-systems': 'Seleziona tutti i sistemi',
    'setup.clear-systems': 'Cancella selezione',
    'setup.select-all-assets': 'Seleziona tutti gli asset',
    'setup.clear-assets': 'Cancella selezione',
    'setup.parameters': 'Parametri',
    'setup.from': 'Da',
    'setup.to': 'A',
    'setup.deposit': 'Deposito',
    'setup.min-retention': 'Retention minima %',
    'setup.start-run': 'Avvia run',
    'auto-modal.title': 'Cosa fa la Modalità Automatica',
    'auto-modal.p1': "La Modalità Automatica fa evolvere l'addestramento da sola: testa ogni asset reale rilevato su questo account/terminale, su tutti gli 11 sistemi, in ordine di rischio (prima i sistemi di ricerca, poi il grid con conto hedging, infine i sistemi di recupero ad alto rischio). Riprende da dove si era interrotta usando il ledger/cache esistente -- nulla di già validato viene rifatto.",
    'auto-modal.p2': "Questo può girare continuamente per molto tempo (una scansione completa di tutti gli asset e sistemi è realisticamente di settimane o mesi, non ore). Segue la stessa metodologia a livelli di rischio descritta in PLANO_TREINAMENTO_100_A_MILHAO.md.",
    'auto-modal.p3': "Se vuoi scegliere esattamente quali sistemi e asset eseguire, usa invece la Modalità Manuale -- niente viene rimosso, entrambe le modalità restano disponibili.",
    'auto-modal.dont-ask': 'Non mostrare più questo messaggio su questo browser',
    'auto-modal.confirm': 'Capito, avvia Automatica',
    'auto-modal.prefer-manual': 'Preferisco usare la Modalità Manuale',
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
    'nav.implantacao': 'Развёртывание',
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
    'setup.select-all-systems': 'Выбрать все системы',
    'setup.clear-systems': 'Очистить выбор',
    'setup.select-all-assets': 'Выбрать все активы',
    'setup.clear-assets': 'Очистить выбор',
    'setup.parameters': 'Параметры',
    'setup.from': 'С',
    'setup.to': 'По',
    'setup.deposit': 'Депозит',
    'setup.min-retention': 'Минимальный retention %',
    'setup.start-run': 'Запустить прогон',
    'auto-modal.title': 'Что делает Автоматический режим',
    'auto-modal.p1': 'Автоматический режим сам развивает обучение: он тестирует каждый реальный актив, обнаруженный на этом счёте/терминале, по всем 11 системам, в порядке риска (сначала исследовательские системы, затем grid с хедж-счётом, затем системы восстановления высокого риска в конце). Он продолжает с того места, где остановился, используя существующий журнал/кэш -- уже проверенное не повторяется.',
    'auto-modal.p2': 'Это может работать непрерывно очень долго (полный проход по всем активам и системам реалистично занимает недели-месяцы, а не часы). Следует той же методологии по уровням риска, описанной в PLANO_TREINAMENTO_100_A_MILHAO.md.',
    'auto-modal.p3': 'Если вы хотите точно выбрать, какие системы и активы запускать, используйте вместо этого Ручной режим -- ничего не удаляется, оба режима остаются доступны.',
    'auto-modal.dont-ask': 'Больше не показывать это в этом браузере',
    'auto-modal.confirm': 'Понятно, запустить Автоматический',
    'auto-modal.prefer-manual': 'Предпочитаю Ручной режим',
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
    'nav.implantacao': '部署',
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
    'setup.select-all-systems': '选择所有系统',
    'setup.clear-systems': '清除选择',
    'setup.select-all-assets': '选择所有资产',
    'setup.clear-assets': '清除选择',
    'setup.parameters': '参数',
    'setup.from': '起始',
    'setup.to': '结束',
    'setup.deposit': '入金',
    'setup.min-retention': '最低留存率 %',
    'setup.start-run': '开始运行',
    'auto-modal.title': '自动模式的作用',
    'auto-modal.p1': '自动模式会自行推进训练：它会测试此账户/终端上检测到的每一个真实资产，覆盖全部11个系统，按风险顺序进行(先测试研究类系统，然后是需要对冲账户的网格系统，最后是高风险的恢复类系统)。它会利用现有的台账/缓存从上次停止的地方继续 -- 已经验证过的内容不会重复测试。',
    'auto-modal.p2': '此过程可能会持续运行很长时间(对所有资产和系统进行一次完整扫描现实上需要数周到数月，而不是几小时)。遵循 PLANO_TREINAMENTO_100_A_MILHAO.md 中描述的相同风险分级方法。',
    'auto-modal.p3': '如果您想精确选择运行哪些系统和资产，请改用手动模式 -- 不会移除任何功能，两种模式都保持可用。',
    'auto-modal.dont-ask': '此浏览器不再显示此提示',
    'auto-modal.confirm': '知道了，启动自动模式',
    'auto-modal.prefer-manual': '我更愿意使用手动模式',
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
    'nav.implantacao': 'デプロイ',
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
    'setup.select-all-systems': 'すべてのシステムを選択',
    'setup.clear-systems': '選択を解除',
    'setup.select-all-assets': 'すべての資産を選択',
    'setup.clear-assets': '選択を解除',
    'setup.parameters': 'パラメータ',
    'setup.from': '開始',
    'setup.to': '終了',
    'setup.deposit': '入金額',
    'setup.min-retention': '最小リテンション %',
    'setup.start-run': '実行を開始',
    'auto-modal.title': '自動モードの動作について',
    'auto-modal.p1': '自動モードはトレーニングを自律的に進めます。このアカウント/端末で検出されたすべての実資産を、11のシステム全てにわたってリスク順(まずリサーチ系システム、次にヘッジ口座が必要なグリッド、最後に高リスクのリカバリー系システム)でテストします。既存の台帳/キャッシュを使って中断した箇所から再開します -- 既に検証済みのものはやり直しません。',
    'auto-modal.p2': 'これは非常に長時間、継続的に実行される可能性があります(すべての資産とシステムを一巡するには、現実的には数時間ではなく数週間から数ヶ月かかります)。PLANO_TREINAMENTO_100_A_MILHAO.md に記載されているのと同じリスク階層別の方法論に従います。',
    'auto-modal.p3': '実行するシステムと資産を正確に選びたい場合は、代わりに手動モードを使用してください -- 何も削除されず、両方のモードが引き続き利用可能です。',
    'auto-modal.dont-ask': 'このブラウザでは今後表示しない',
    'auto-modal.confirm': '理解しました、自動モードを開始',
    'auto-modal.prefer-manual': '手動モードを使いたい',
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
    'nav.implantacao': '배포',
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
    'setup.select-all-systems': '모든 시스템 선택',
    'setup.clear-systems': '선택 해제',
    'setup.select-all-assets': '모든 자산 선택',
    'setup.clear-assets': '선택 해제',
    'setup.parameters': '파라미터',
    'setup.from': '시작일',
    'setup.to': '종료일',
    'setup.deposit': '입금액',
    'setup.min-retention': '최소 리텐션 %',
    'setup.start-run': '실행 시작',
    'auto-modal.title': '자동 모드가 하는 일',
    'auto-modal.p1': '자동 모드는 트레이닝을 스스로 진행합니다: 이 계정/터미널에서 감지된 모든 실제 자산을 11개 시스템 전체에서, 위험 순서대로(연구용 시스템 먼저, 그다음 헤지 계좌가 필요한 그리드, 마지막으로 고위험 리커버리 시스템) 테스트합니다. 기존 원장/캐시를 사용하여 중단한 지점부터 재개합니다 -- 이미 검증된 항목은 다시 실행하지 않습니다.',
    'auto-modal.p2': '이 작업은 매우 오랫동안 계속 실행될 수 있습니다(모든 자산과 시스템을 한 번 완전히 훑는 데 현실적으로 몇 시간이 아니라 몇 주에서 몇 달이 걸립니다). PLANO_TREINAMENTO_100_A_MILHAO.md에 설명된 것과 동일한 위험 등급별 방법론을 따릅니다.',
    'auto-modal.p3': '정확히 어떤 시스템과 자산을 실행할지 직접 선택하고 싶다면 대신 수동 모드를 사용하세요 -- 아무것도 제거되지 않으며 두 모드 모두 계속 사용할 수 있습니다.',
    'auto-modal.dont-ask': '이 브라우저에서 다시 표시하지 않음',
    'auto-modal.confirm': '이해했습니다, 자동 모드 시작',
    'auto-modal.prefer-manual': '수동 모드를 사용하고 싶습니다',
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
    'nav.implantacao': 'Dağıtım',
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
    'setup.select-all-systems': 'Tüm sistemleri seç',
    'setup.clear-systems': 'Seçimi temizle',
    'setup.select-all-assets': 'Tüm varlıkları seç',
    'setup.clear-assets': 'Seçimi temizle',
    'setup.parameters': 'Parametreler',
    'setup.from': 'Başlangıç',
    'setup.to': 'Bitiş',
    'setup.deposit': 'Depozito',
    'setup.min-retention': 'Minimum retention %',
    'setup.start-run': 'Çalıştırmayı başlat',
    'auto-modal.title': 'Otomatik Modun yaptığı şey',
    'auto-modal.p1': 'Otomatik Mod, eğitimi kendi kendine geliştirir: bu hesapta/terminalde tespit edilen her gerçek varlığı, 11 sistemin tamamında, risk sırasına göre (önce araştırma sistemleri, ardından hedge hesabı gerektiren grid, en son yüksek riskli kurtarma sistemleri) test eder. Mevcut kayıt defteri/önbelleği kullanarak kaldığı yerden devam eder -- zaten doğrulanmış hiçbir şey tekrar yapılmaz.',
    'auto-modal.p2': 'Bu, çok uzun süre kesintisiz çalışabilir (tüm varlıklar ve sistemler üzerinde tam bir tarama gerçekçi olarak saatler değil, haftalar-aylar sürer). PLANO_TREINAMENTO_100_A_MILHAO.md dosyasında açıklanan aynı risk katmanlı metodolojiyi izler.',
    'auto-modal.p3': 'Tam olarak hangi sistemlerin ve varlıkların çalışacağını seçmek isterseniz, bunun yerine Manuel Modu kullanın -- hiçbir şey kaldırılmaz, her iki mod da kullanılabilir kalır.',
    'auto-modal.dont-ask': 'Bu tarayıcıda bir daha gösterme',
    'auto-modal.confirm': 'Anladım, Otomatiği başlat',
    'auto-modal.prefer-manual': 'Manuel Modu tercih ederim',
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
let recentesAtuais = [];
document.querySelector("#tbl-recentes").addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-chave]");
  if (!btn) return;
  const chave = btn.dataset.chave;
  const abrindo = !linhasExpandidas.has(chave);
  if (abrindo) linhasExpandidas.add(chave);
  else linhasExpandidas.delete(chave);
  const idLinha = "det-" + chave.replace(/[^a-zA-Z0-9]/g, "_");
  document.getElementById(idLinha)?.classList.toggle("linha-oculta");
  if (abrindo) {
    const r = recentesAtuais.find((x) =>
      `${x.simbolo}|${x.sistema}|${x.variante}|${x.quando}` === chave);
    if (r && r.relatorio_dir) {
      carregarResumoRelatorio(r.relatorio_dir, "conf_wrx", "resumo-" + idLinha);
    }
  }
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
  recentesAtuais = d.recentes;
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
      ${r.relatorio_dir ? `<div id="resumo-${idLinha}" class="detalhe-grid"><span class="status-msg">loading summary...</span></div>` : ""}
      <div class="detalhe-grid">
        <span>lucro OHLC/busca: <b>${r.lucro_ohlc ?? "-"}</b></span>
        <span>lucro tick real: <b>${r.lucro_tick_real ?? "-"}</b></span>
        <span>lucro ajustado (custo nativo): <b>${r.lucro_ajustado_custo_nativo ?? "n/d"}</b></span>
        <span>retenção %: <b>${r.retencao_pct ?? "-"}</b></span>
        <span>sizing entregue: <b>${r.sizing_entrega ?? "-"}</b></span>
        <span>${mc}</span>
        ${r.relatorio_dir ? `<span><a href="/relatorios/${r.relatorio_dir}/conf_wrx.htm" target="_blank">relatório completo ↗</a></span>` : ""}
      </div>
      ${r.relatorio_dir ? `
      <div class="detalhe-grid" style="margin-top:8px">
        <span>Equity/balance history:</span>
        <img src="/relatorios/${r.relatorio_dir}/conf_wrx-hst.png" style="max-width:100%;border:1px solid var(--line);border-radius:6px;margin-top:4px" alt="Equity/balance history" onerror="this.style.display='none'">
        <span>MFE/MAE scatter:</span>
        <img src="/relatorios/${r.relatorio_dir}/conf_wrx-mfemae.png" style="max-width:100%;border:1px solid var(--line);border-radius:6px;margin-top:4px" alt="MFE/MAE scatter" onerror="this.style.display='none'">
        <span>Position holding time:</span>
        <img src="/relatorios/${r.relatorio_dir}/conf_wrx-holding.png" style="max-width:100%;border:1px solid var(--line);border-radius:6px;margin-top:4px" alt="Position holding time" onerror="this.style.display='none'">
      </div>` : ""}
      </td></tr>`;
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

  // Progresso do combo atual (achado do dono, 2026-08-07): sem isso, uma
  // campanha lenta (grid pode passar de 2h so no Estagio 1) e
  // indistinguivel de travada -- so "rodando: true" sem nenhum detalhe.
  const badgeP = document.getElementById("badge-progresso");
  const p = e.progresso;
  if (p && p.symbol) {
    const partes = [p.symbol, p.sistema, p.variante, p.estagio,
      p.rodada ? `rodada ${p.rodada}` : null,
      p.finalista_atual ? `finalista ${p.finalista_atual}` : null,
    ].filter(Boolean);
    badgeP.textContent = partes.join(" | ");
    badgeP.title = "atualizado " + (p.atualizado_em || "");
    badgeP.style.display = "";
  } else {
    badgeP.style.display = "none";
  }
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
function anosAtrasMT5(anos) {
  const d = new Date();
  d.setFullYear(d.getFullYear() - anos);
  const dois = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}.${dois(d.getMonth() + 1)}.${dois(d.getDate())}`;
}
document.getElementById("campo-fim").value = hojeMT5();
document.getElementById("perfil-wfo-fim").value = hojeMT5();
// "From" vinha cravado em "2023.08.01" no HTML -- ficava mais desatualizado
// a cada dia (achado 2026-08-06, quase 3 anos de defasagem). Sugestao
// sempre relativa a hoje: 3 anos pra tras, igual ao --from default do
// campanha.py quando chamado sem esse dashboard.
document.getElementById("campo-inicio").value = anosAtrasMT5(3);

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
  document.getElementById("check-sistemas").innerHTML = CONFIG.sistemas.map((s, i) => {
    const nota = !s.capital_aplica ? "n/a (fixed lot)"
      : s.capital_agregado > 0 ? `validated capital: ${s.capital_agregado.toLocaleString()}`
      : "no validated capital yet";
    return `<label><input type="checkbox" class="chk-sistema" value="${s.code}" ${i < 2 ? "checked" : ""}>
      ${s.code} — ${s.label} <span class="capital-note">(${nota})</span></label>`;
  }).join("");
  const grupos = document.getElementById("grupos-ativos");
  grupos.innerHTML = Object.entries(CONFIG.classes).map(([classe, info]) => `
    <fieldset><legend>${classe} (capital base ${info.capital_base})
      <button type="button" class="btn-classe-todos">all</button>
      <button type="button" class="btn-classe-nenhum">none</button>
    </legend>
    <div class="grid-check">${info.ativos.map((a) =>
      `<label><input type="checkbox" class="chk-ativo" value="${a}"> ${a}</label>`).join("")}</div>
    </fieldset>`).join("");
}
carregarConfig();

document.getElementById("btn-sistemas-todos").addEventListener("click", () =>
  document.querySelectorAll(".chk-sistema").forEach((c) => { c.checked = true; }));
document.getElementById("btn-sistemas-nenhum").addEventListener("click", () =>
  document.querySelectorAll(".chk-sistema").forEach((c) => { c.checked = false; }));
document.getElementById("btn-ativos-todos").addEventListener("click", () =>
  document.querySelectorAll(".chk-ativo").forEach((c) => { c.checked = true; }));
document.getElementById("btn-ativos-nenhum").addEventListener("click", () =>
  document.querySelectorAll(".chk-ativo").forEach((c) => { c.checked = false; }));
document.getElementById("grupos-ativos").addEventListener("click", (ev) => {
  const todos = ev.target.closest(".btn-classe-todos");
  const nenhum = ev.target.closest(".btn-classe-nenhum");
  if (!todos && !nenhum) return;
  ev.target.closest("fieldset").querySelectorAll(".chk-ativo")
    .forEach((c) => { c.checked = !!todos; });
});

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
    // descobrir_ativos.py rodado standalone (main(), nao carregar_ou_descobrir())
    // imprime um simbolo por linha, indentado com 2 espacos -- nao a lista
    // entre parenteses que este parser esperava antes (achado 2026-08-06,
    // debugando "Detectar" clicado e nada era marcado): o regex antigo nunca
    // batia com a saida real, "nomes" ficava vazio e nada era resolvido, o
    // que por sua vez fazia o fix do sufixo (acima) nunca disparar.
    const nomes = (j.saida || "").split("\n")
      .map((l) => (l.match(/^  ([A-Z0-9.]+)\s*$/) || [])[1])
      .filter(Boolean);
    if (!nomes.length) return;
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

async function iniciarCorridaReal() {
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
}

// Modal do Modo Automatico (dono, 2026-08-08): explica o que o modo faz
// (evolui sozinho, testa tudo, ordem de risco, pode levar semanas/meses)
// ANTES de disparar -- so pra Automatico, nunca pro Manual, que ja e uma
// escolha explicita passo a passo. "Nao mostrar de novo" fica por
// navegador (localStorage), nao no servidor -- decisao do cliente que
// esta na frente da tela, nao algo pra sincronizar entre maquinas.
const CHAVE_AUTO_OK = "wrx_auto_modal_dispensado";
document.getElementById("btn-iniciar").addEventListener("click", () => {
  if (modoAtual === "auto" && localStorage.getItem(CHAVE_AUTO_OK) !== "1") {
    document.getElementById("modal-auto").style.display = "flex";
    return;
  }
  iniciarCorridaReal();
});
document.getElementById("btn-auto-confirmar").addEventListener("click", () => {
  if (document.getElementById("chk-auto-nao-perguntar").checked) {
    localStorage.setItem(CHAVE_AUTO_OK, "1");
  }
  document.getElementById("modal-auto").style.display = "none";
  iniciarCorridaReal();
});
document.getElementById("btn-auto-manual").addEventListener("click", () => {
  document.getElementById("modal-auto").style.display = "none";
  setModo("manual");
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
let portfolioCapital = {};

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
  portfolioCapital = d.capital_por_sistema || {};
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
  const capital = portfolioCapital[nome];
  const badge = document.getElementById("portfolio-sistema-capital");
  if (capital) {
    badge.style.display = "";
    badge.innerHTML = `<div class="metric-label">Validated capital</div><b>${capital.toLocaleString()}</b>`;
  } else {
    badge.style.display = "none";
  }
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
async function carregarResumoRelatorio(dir, nome, elId) {
  const el = document.getElementById(elId);
  if (!el || el.dataset.carregado) return;
  el.dataset.carregado = "1";
  const r = await api(`/api/relatorio/${encodeURIComponent(dir)}/resumo?nome=${nome}`);
  if (!r.ok) { el.innerHTML = `<span class="status-msg">${r.erro || "summary unavailable"}</span>`; return; }
  const m = r.resumo;
  const linha = (rot, v) => `<span>${rot}: <b>${v ?? "-"}</b></span>`;
  el.innerHTML = [
    linha("Profit factor", m.profit_factor),
    linha("Recovery factor", m.recovery_factor),
    linha("Sharpe ratio", m.sharpe_ratio),
    linha("Balance DD (rel.)", m.balance_dd_relative),
    linha("Max consecutive wins", m.max_consecutive_wins),
    linha("Max consecutive losses", m.max_consecutive_losses),
  ].join("");
}

const implantacaoExpandida = new Set();
document.querySelector("#tbl-implantacao").addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-grafico]");
  if (!btn) return;
  const chave = btn.dataset.grafico;
  const abrindo = !implantacaoExpandida.has(chave);
  if (abrindo) implantacaoExpandida.add(chave);
  else implantacaoExpandida.delete(chave);
  const idGraf = "graf-" + chave.replace(/[^a-zA-Z0-9]/g, "_");
  document.getElementById(idGraf)?.classList.toggle("linha-oculta");
  if (abrindo) {
    const set = implantacaoSets.find((s) => s.chave === chave);
    if (set) carregarResumoRelatorio(set.relatorio_dir, "sobrevivencia", "resumo-" + idGraf);
  }
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
      <div id="resumo-${idGraf}" class="detalhe-grid"><span class="status-msg">loading summary...</span></div>
      <div class="detalhe-grid" style="margin-top:8px">
        <span>Full-period equity curve (the one the survival gate actually measured — not the short OOS window):</span>
        <img src="/relatorios/${s.relatorio_dir}/sobrevivencia.png" style="max-width:100%;border:1px solid var(--line);border-radius:6px;margin-top:4px" alt="Full-period equity curve">
        <span>Equity/balance history:</span>
        <img src="/relatorios/${s.relatorio_dir}/sobrevivencia-hst.png" style="max-width:100%;border:1px solid var(--line);border-radius:6px;margin-top:4px" alt="Equity/balance history" onerror="this.style.display='none'">
        <span>MFE/MAE scatter:</span>
        <img src="/relatorios/${s.relatorio_dir}/sobrevivencia-mfemae.png" style="max-width:100%;border:1px solid var(--line);border-radius:6px;margin-top:4px" alt="MFE/MAE scatter" onerror="this.style.display='none'">
        <span>Position holding time:</span>
        <img src="/relatorios/${s.relatorio_dir}/sobrevivencia-holding.png" style="max-width:100%;border:1px solid var(--line);border-radius:6px;margin-top:4px" alt="Position holding time" onerror="this.style.display='none'">
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
