// Existe so para o navegador considerar o dashboard instalavel como app
// (display: standalone no manifest). Sem cache proprio de proposito -- os
// dados aqui sao ao vivo (campanha rodando, ledger mudando a cada combo);
// cachear a resposta envelheceria o painel silenciosamente.
self.addEventListener("fetch", () => {});
