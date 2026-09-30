"""Posicoes, ordens pendentes, deals e o estado derivado do historico (recovery, D'Alembert, grid, piramide).

Espelha o que o EA reconstroi de HistorySelect(): `RefreshClosedOperations` (um resultado por posicao
totalmente fechada, com comissao/swap agregados), `ApplyRecoveryOperation`, `RefreshDAlembertState` e os
estados `g_grid*` / `g_pyramid*`. Aqui tudo e incremental: cada fechamento chama `close_operation`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

EPS = 0.0000001


@dataclass
class Pos:
    ticket: int
    is_buy: bool
    volume: float
    open_price: float
    open_ms: int
    sl: float
    tp: float
    tag: str = ""
    swap: float = 0.0
    commission: float = 0.0          # comissao da ENTRADA (ja cobrada ao abrir)
    seed_order: int = 0              # ordem-semente do ciclo de grid (para o alvo congelado)


@dataclass
class Pend:
    ticket: int
    kind: str                        # buy_stop | buy_limit | sell_stop | sell_limit
    price: float
    volume: float
    sl: float
    tp: float
    setup_ms: int
    tag: str = ""

    @property
    def is_buy(self) -> bool:
        return self.kind.startswith("buy")


@dataclass
class Op:
    """Operacao fechada (DealNetResult agregado da posicao)."""
    ticket: int
    side: int                        # +1 compra, -1 venda
    volume: float
    net: float
    close_ms: int
    open_ms: int


@dataclass
class Recovery:
    operations: int = 0
    wins: int = 0
    losses: int = 0
    consecutive_losses: int = 0
    gross_loss: float = 0.0
    recovered: float = 0.0
    outstanding: float = 0.0
    cycle_start: int = 0
    limit_resets: int = 0
    force_base_next: bool = False

    def clear(self, force_base_next: bool) -> None:
        resets = self.limit_resets + (1 if force_base_next else 0)
        self.operations = self.wins = self.losses = self.consecutive_losses = 0
        self.gross_loss = self.recovered = self.outstanding = 0.0
        self.cycle_start = 0
        self.limit_resets = resets
        self.force_base_next = force_base_next

    def apply(self, net: float, close_ms: int, max_steps: int) -> None:
        """ApplyRecoveryOperation()."""
        if self.force_base_next:
            self.force_base_next = False
        if net < -EPS:
            if self.outstanding <= EPS:
                self.cycle_start = close_ms // 1000
            self.operations += 1
            self.losses += 1
            self.consecutive_losses += 1
            self.gross_loss += abs(net)
            self.outstanding += abs(net)
            if max_steps > 0 and self.consecutive_losses > max_steps:
                self.clear(True)
            return
        if self.outstanding <= EPS:
            return
        self.operations += 1
        self.consecutive_losses = 0
        if net > EPS:
            self.wins += 1
            applied = min(net, self.outstanding)
            self.recovered += applied
            self.outstanding -= applied
            if self.outstanding <= EPS:
                self.clear(False)


@dataclass
class GridSide:
    cycle_start: int = 0             # s (0 = sem ciclo)
    realized: float = 0.0
    target: float = 0.0
    seed_order: int = 0
    seed_ppl: float = 0.0            # lucro por lote no momento da semente


@dataclass
class PyramidSide:
    cycle_start: int = 0
    peak: float = 0.0


@dataclass
class Ledger:
    deposit: float
    positions: list = field(default_factory=list)
    pendings: list = field(default_factory=list)
    ops: list = field(default_factory=list)
    realized: float = 0.0            # soma liquida de TODOS os deals (inclui comissao de entrada e swap)
    withdrawn: float = 0.0
    next_ticket: int = 1
    rec: dict = field(default_factory=lambda: {1: Recovery(), -1: Recovery()})
    dal: dict = field(default_factory=lambda: {1: 0, -1: 0})
    grid: dict = field(default_factory=lambda: {1: GridSide(), -1: GridSide()})
    pyr: dict = field(default_factory=lambda: {1: PyramidSide(), -1: PyramidSide()})
    last_entry_s: int = -10**12      # g_lastAcceptedOpenTime / ultimo deal de entrada

    @property
    def balance(self) -> float:
        return self.deposit + self.realized - self.withdrawn

    def new_ticket(self) -> int:
        t = self.next_ticket
        self.next_ticket += 1
        return t

    # ------------------------------------------------------------ consultas do EA
    def count(self, side: int) -> int:
        return sum(1 for p in self.positions if (p.is_buy if side > 0 else not p.is_buy))

    def of_side(self, side: int) -> list:
        return [p for p in self.positions if (p.is_buy if side > 0 else not p.is_buy)]

    def last_trade(self, side: int):
        """LastTradePrice/LastTradeVolume: a posicao ABERTA mais recente do lado (por tempo em ms)."""
        best = None
        for p in self.of_side(side):
            if best is None or p.open_ms >= best.open_ms:
                best = p
        return best

    def last_closed(self, side: int):
        """GetLastClosedOperation(): ultima operacao FECHADA do lado."""
        for op in reversed(self.ops):
            if op.side == side:
                return op
        return None

    def pend_count(self, side: int) -> int:
        return sum(1 for o in self.pendings if (o.is_buy if side > 0 else not o.is_buy))

    # ------------------------------------------------------------ fechamento
    def close_operation(self, pos: Pos, net: float, close_ms: int, max_steps: int, dalembert: bool) -> Op:
        side = 1 if pos.is_buy else -1
        op = Op(pos.ticket, side, pos.volume, net, close_ms, pos.open_ms)
        self.ops.append(op)
        self.rec[side].apply(net, close_ms, max_steps)
        if dalembert:
            lvl = self.dal[side]
            if net < 0.0:
                lvl += 1
            elif net > 0.0:
                lvl = max(0, lvl - 1)
            if max_steps > 0:
                lvl = min(lvl, max_steps)
            self.dal[side] = lvl
        return op
