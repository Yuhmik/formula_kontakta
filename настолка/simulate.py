#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Симулятор баланса карточной игры "Формула улёта".

ДЕРЖАТЬ В СИНХРОНЕ С Формула_улёта_правила.md. Если меняются суммы, состав карт,
цель корабля или порядок разрешения фазы — правьте PARAMS / CARDS / RANK /
resolve_phase() здесь же, в первую очередь.

Модель разрешения фазы (текущая): игроки одновременно и тайно кладут одну
карту из руки. Дальше карты вскрываются ПО КРУГУ, начиная с игрока-держателя
маркера первого хода (маркер переходит по кругу после каждой фазы). Раскрыв
свою карту, игрок с «Обыском»/«Смутой» тут же называет цель (пальцем/по
месту, без слов) — он уже видит карты вскрывшихся до него в этой же фазе, но
не тех, кто вскроется позже. Настоящая (историческая) альтернатива —
разрешение по рангу при одновременном вскрытии, без такой информации,
оставлена как RESOLUTION_MODE = "rank" для сравнения.

Игроки моделируются не как "оптимальные боты", а как приближение к живым
людям: у каждого есть СТИЛЬ (что вообще предпочитает), ПОСЛЕДОВАТЕЛЬНОСТЬ
(насколько строго стиля придерживается вместо случайного хода) и
ВНИМАТЕЛЬНОСТЬ (насколько использует доступную информацию, целясь
"Обыском"/"Смутой", вместо удара наугад).

Запуск:
    python simulate.py            # весь стандартный набор сценариев
    python simulate.py --quick    # только несколько ключевых сценариев (быстрее)
"""

import argparse
import random
import sys
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# ПАРАМЕТРЫ ИГРЫ
# ---------------------------------------------------------------------------

PARAMS = dict(
    n_tacts=3,
    start_money=3000,
    obrok_value=500,
    promysel_value=1000,
    obysk_steal=1000,
    finish_bonus=2000,
    participant_bonus=1000,
    fail_penalty=500,
    artifact_value=1000,
)

CARDS = ["OBYSK", "SMUTA", "VZYATKA", "PROMYSEL", "OBROK", "LOG"]
RANK = {"OBYSK": 6, "SMUTA": 5, "VZYATKA": 4, "PROMYSEL": 3, "OBROK": 2, "LOG": 1}
N_PHASES = len(CARDS)

RESOLUTION_MODE = "ring"  # "ring" (текущие правила) или "rank" (для сравнения)


def ship_target(n_players):
    return n_players


# ---------------------------------------------------------------------------
# ПРОФИЛИ ИГРОКОВ
# ---------------------------------------------------------------------------
# style        — что игрок вообще предпочитает делать
# consistency  — 0..1, насколько строго следует стилю (1 = всегда по стилю,
#                0 = фактически ходит наугад)
# attention    — 0..1, насколько осознанно выбирает цель "Обыска"/"Смуты"
#                (1 = использует всю доступную информацию, 0 = наугад)

STYLE_ORDER = {
    "econ":   ["PROMYSEL", "OBROK", "LOG", "VZYATKA", "OBYSK", "SMUTA"],
    "aggro":  ["OBYSK", "SMUTA", "PROMYSEL", "OBROK", "LOG", "VZYATKA"],
    "turtle": ["VZYATKA", "OBROK", "PROMYSEL", "LOG", "OBYSK", "SMUTA"],
    # Гонщик играет "Промысел" рано, БЕЗ попытки выждать безопасный момент -
    # проверено симуляцией, что отсрочка (ждать, пока соперники сыграют свою
    # "Смуту") не снижает риск блокировки, а повышает его: у части стилей
    # "Смута" сама в конце приоритета, и "безопасный" момент часто наступает
    # только на последней фазе такта, где все одновременно разыгрывают
    # последнюю оставшуюся карту - там и происходит основная масса
    # столкновений. Ранний розыгрыш (пока большинство соперников ещё не
    # готовы играть "Смуту") статистически безопаснее любой отсрочки.
    "racer":  ["PROMYSEL", "LOG", "OBROK", "VZYATKA", "OBYSK", "SMUTA"],
    # Уравновешенный: не гонится за бочкой любой ценой (не в приоритете
    # "Обыск"/"Смута" - не агрессор), но и не сбрасывает Промысел в деньги
    # почти всегда, как эконом - золотая середина между стилями.
    "balanced": ["PROMYSEL", "OBROK", "VZYATKA", "LOG", "OBYSK", "SMUTA"],
}

BARREL_BASE_PROB = {
    "econ": 0.05, "aggro": 0.20, "turtle": 0.20, "racer": 0.85,
    "adaptive": 0.30, "balanced": 0.50,
}

# "Хаотичный" не имеет одного фиксированного уровня небрежности - при
# создании каждого такого игрока (см. Player.__init__) его согласованность и
# внимательность заново тянутся случайно из [0, CHAOTIC_MAX_LEVEL], каждую
# партию заново. Так один профиль честно покрывает весь диапазон "от играющего
# совсем наугад до слегка осмысленного", а не одну произвольную точку.
CHAOTIC_MAX_LEVEL = 0.35


class Profile:
    def __init__(self, name, style, consistency=1.0, attention=1.0, memory=1.0, random_spread=0.0):
        self.name = name
        self.style = style
        self.consistency = consistency  # логичность: следует своему стилю, а не наугад
        self.attention = attention      # внимание: замечает, что уже вскрыто в ЭТУ фазу
        self.memory = memory            # память: помнит, что разыграно РАНЬШЕ в этом такте
        # random_spread > 0: каждая партия (в Player.__init__) все три числа
        # заново дрожат на ±spread вокруг заданных здесь значений - так
        # "средний по стилю" профиль превращается в разброс вокруг среднего,
        # а не одну и ту же фиксированную точку из партии в партию.
        self.random_spread = random_spread

    def label(self):
        tag = []
        if self.consistency < 0.99:
            tag.append(f"согл={self.consistency:.2f}")
        if self.attention < 0.99:
            tag.append(f"вним={self.attention:.2f}")
        if self.memory < 0.99:
            tag.append(f"память={self.memory:.2f}")
        suffix = f" ({', '.join(tag)})" if tag else ""
        return f"{self.name}{suffix}"


class Player:
    def __init__(self, pid, profile):
        self.pid = pid
        self.profile = profile
        self.money = PARAMS["start_money"]
        self.barrels = []          # запас недовезённых бочек ("oil"/"spirit")
        self.contributed = set()   # какие типы топлива хоть раз довозил
        self.delivered = 0         # сколько бочек лично довёз за игру (для тай-брейка)
        self.is_finisher = False   # довёз именно решающую бочку
        self.attacked_last_phase = False
        # У "хаотичного" эти значения заново случайны каждую партию (см.
        # CHAOTIC_MAX_LEVEL выше). У остальных стилей с random_spread>0 -
        # дрожат вокруг заданного в профиле среднего. При random_spread=0
        # (по умолчанию, "идеальные" боты) - остаются точно как в профиле.
        if profile.style == "chaotic":
            self.consistency = random.uniform(0, CHAOTIC_MAX_LEVEL)
            self.attention = random.uniform(0, CHAOTIC_MAX_LEVEL)
            self.memory = random.uniform(0, CHAOTIC_MAX_LEVEL)
        elif profile.random_spread > 0:
            s = profile.random_spread
            self.consistency = min(1.0, max(0.0, profile.consistency + random.uniform(-s, s)))
            self.attention = min(1.0, max(0.0, profile.attention + random.uniform(-s, s)))
            self.memory = min(1.0, max(0.0, profile.memory + random.uniform(-s, s)))
        else:
            self.consistency = profile.consistency
            self.attention = profile.attention
            self.memory = profile.memory

    def reset_tact(self):
        self.hand = set(CARDS)


class GameState:
    def __init__(self, players):
        self.players = players
        self.ship = {"oil": 0, "spirit": 0}
        self.snapshot = {}  # деньги на начало текущей фазы, pid -> money
        self.ring_start = 0  # кто вскрывается первым в эту фазу (публично известно заранее)


# ---------------------------------------------------------------------------
# ВЫБОР ХОДА
# ---------------------------------------------------------------------------

def adaptive_order(player, state):
    n = len(state.players)
    avg_money = sum(p.money for p in state.players) / n
    remaining = ship_target(n) - max(state.ship.values())
    order = []
    if remaining <= 2:
        order += ["PROMYSEL", "LOG"]
    if player.attacked_last_phase:
        order.append("VZYATKA")
    if player.money < avg_money * 0.8:
        order += ["OBYSK", "SMUTA", "PROMYSEL"]
    elif player.money > avg_money * 1.2:
        order.append("VZYATKA")
    for c in ["PROMYSEL", "OBROK", "VZYATKA", "LOG", "OBYSK", "SMUTA"]:
        if c not in order:
            order.append(c)
    return order


def style_order(player, state):
    style = player.profile.style
    if style == "chaotic":
        order = CARDS[:]
        random.shuffle(order)
        return order
    if style == "adaptive":
        return adaptive_order(player, state)
    return STYLE_ORDER[style]


def choose_card(player, state):
    if random.random() < player.consistency:
        for c in style_order(player, state):
            if c in player.hand:
                return c
    return random.choice(list(player.hand))


def barrel_choice_prob(player, state):
    if player.profile.style == "chaotic":
        # Честная случайность: 1/3 деньги, 1/3 нефть, 1/3 самогон - без
        # оглядки на то, насколько корабль близок к цели.
        return 2 / 3
    base = BARREL_BASE_PROB.get(player.profile.style, 0.2)
    n = len(state.players)
    remaining = ship_target(n) - max(state.ship.values())
    if remaining <= 2:
        base = max(base, 0.75)
    noise = (1 - player.consistency) * 0.25
    return min(1.0, max(0.0, base + random.uniform(-noise, noise)))


def pick_fuel_type(state, style=None):
    if style == "chaotic":
        return random.choice(["oil", "spirit"])
    if state.ship["oil"] == state.ship["spirit"]:
        return random.choice(["oil", "spirit"])
    return "oil" if state.ship["oil"] > state.ship["spirit"] else "spirit"


def choose_target(player, state, revealed_so_far, played_this_tact, want_smuta):
    """Три независимых качества игрока, три тира приоритета цели:
    - attention (внимание): вообще пытается ли целиться осознанно, а не
      наугад - ворота на входе в функцию.
    - тир 1: кто уже вскрылся в ЭТУ ФАЗУ с нужной/опасной картой -
      максимально достоверно прямо сейчас, не требует memory (это же не
      "вспоминание", а то, что только что произошло на глазах).
    - memory (память): помнит ли, что разыграно РАНЬШЕ в этом такте, чтобы
      применить тир 2 (для Смуты: уже сыграл "Промысел" раньше - шанс
      нулевой, исключаем; для Обыска: уже сыграл "Взятку" раньше - её больше
      нет, гарантированно уязвим прямо сейчас). Не сработала память - тир 2
      недоступен в эту фазу, будто и не было предыдущих фаз этого такта.
    - тир 3: если кандидатов несколько - добиваем эвристикой: деньги для
      Обыска, бочки в запасе для Смуты.
    """
    others = [p for p in state.players if p is not player]
    if random.random() >= player.attention:
        return random.choice(others)

    if want_smuta:
        tier1 = [p for p in others if revealed_so_far.get(p.pid) == "PROMYSEL"]
        if tier1:
            pool = tier1
        else:
            pool = []
            if random.random() < player.memory:
                pool = [p for p in others
                        if p.pid not in revealed_so_far
                        and "PROMYSEL" not in played_this_tact.get(p.pid, set())]
            if not pool:
                pool = [p for p in others if p.pid not in revealed_so_far] or others
        if len(pool) > 1:
            best = max(len(p.barrels) for p in pool)
            pool = [p for p in pool if len(p.barrels) == best]
    else:
        tier1 = [p for p in others if p.pid in revealed_so_far and revealed_so_far[p.pid] != "VZYATKA"]
        if tier1:
            pool = tier1
        else:
            pool = []
            if random.random() < player.memory:
                pool = [p for p in others
                        if p.pid not in revealed_so_far
                        and "VZYATKA" in played_this_tact.get(p.pid, set())]
            if not pool:
                pool = [p for p in others if p.pid not in revealed_so_far] or others
        if len(pool) > 1:
            best = max(state.snapshot[p.pid] for p in pool)
            pool = [p for p in pool if state.snapshot[p.pid] == best]

    return random.choice(pool)


# ---------------------------------------------------------------------------
# ДВИЖОК ПАРТИИ
# ---------------------------------------------------------------------------

def run_game(profiles):
    players = [Player(i, prof) for i, prof in enumerate(profiles)]
    state = GameState(players)
    n = len(players)
    ship_done = False
    finisher = None
    winning_type = None
    ring_start = 0
    alien_deck = ["BLANK"] * 7 + ["ARTIFACT"] * 3
    max_single = PARAMS["start_money"]
    max_total = PARAMS["start_money"] * n

    for tact in range(PARAMS["n_tacts"]):
        if ship_done:
            break
        for p in players:
            p.reset_tact()
        random.shuffle(alien_deck)  # колода пришельцев пересдаётся в начале такта
        alien_pos = 0
        played_this_tact = {p.pid: set() for p in players}  # для тира 2 в choose_target

        for phase in range(N_PHASES):
            if ship_done:
                break
            state.ring_start = ring_start  # известно заранее, до выбора карт
            plays = {p.pid: choose_card(p, state) for p in players if p.hand}
            for pid, card in plays.items():
                players[pid].hand.discard(card)

            state.snapshot = {p.pid: p.money for p in players}
            promysel_negated = set()
            attacked_this_phase = set()

            if RESOLUTION_MODE == "rank":
                seq = sorted(plays.items(), key=lambda kv: -RANK[kv[1]])
                vzyatka_players = {pid for pid, c in plays.items() if c == "VZYATKA"}
                revealed = dict(plays)  # всё видно сразу — только для сравнения
            else:
                seq = [(pid, plays[pid]) for pid in
                       ((ring_start + i) % n for i in range(n)) if pid in plays]
                vzyatka_players = None  # определяется по ходу (revealed)
                revealed = {}

            for pid, card in seq:
                actor = players[pid]
                if card == "OBYSK":
                    target = choose_target(actor, state, revealed, played_this_tact, want_smuta=False)
                    defended = (target.pid in vzyatka_players) if vzyatka_players is not None \
                        else (plays.get(target.pid) == "VZYATKA")
                    if not defended:
                        steal = min(PARAMS["obysk_steal"], target.money)
                        target.money -= steal
                        actor.money += steal
                        attacked_this_phase.add(target.pid)
                elif card == "SMUTA":
                    target = choose_target(actor, state, revealed, played_this_tact, want_smuta=True)
                    if plays.get(target.pid) == "PROMYSEL":
                        promysel_negated.add(target.pid)
                    attacked_this_phase.add(target.pid)
                elif card == "VZYATKA":
                    pass
                elif card == "PROMYSEL":
                    if pid not in promysel_negated:
                        if random.random() < barrel_choice_prob(actor, state):
                            ftype = pick_fuel_type(state, actor.profile.style)
                            actor.barrels.append(ftype)
                        else:
                            actor.money += PARAMS["promysel_value"]
                elif card == "OBROK":
                    actor.money += PARAMS["obrok_value"]
                elif card == "LOG":
                    if actor.barrels:
                        ftype = actor.barrels.pop(0)
                        state.ship[ftype] += 1
                        actor.contributed.add(ftype)
                        actor.delivered += 1
                        if state.ship[ftype] >= ship_target(n) and not ship_done:
                            ship_done = True
                            finisher = actor.pid
                            winning_type = ftype
                    else:
                        if alien_pos < len(alien_deck):
                            drawn = alien_deck[alien_pos]
                            alien_pos += 1
                            if drawn == "ARTIFACT":
                                actor.money += PARAMS["artifact_value"]
                if RESOLUTION_MODE == "ring":
                    revealed[pid] = card
                if ship_done:
                    # "Как только шкала достигла цели - корабль взлетает, игра
                    # заканчивается" - немедленно, остальные карты этой же
                    # фазы (у ещё не раскрывшихся в этот раз игроков) не
                    # разыгрываются.
                    break

            for p in players:
                p.attacked_last_phase = p.pid in attacked_this_phase

            for pid, card in plays.items():
                played_this_tact[pid].add(card)

            if RESOLUTION_MODE == "ring":
                ring_start = (ring_start + 1) % n

            max_single = max(max_single, max(p.money for p in players))
            max_total = max(max_total, sum(p.money for p in players))

    if ship_done:
        for p in players:
            if p.pid == finisher:
                p.money += PARAMS["finish_bonus"]
                p.is_finisher = True
            elif winning_type in p.contributed:
                p.money += PARAMS["participant_bonus"]
    else:
        for p in players:
            if p.barrels:
                p.money -= PARAMS["fail_penalty"]

    max_single = max(max_single, max(p.money for p in players))
    max_total = max(max_total, sum(p.money for p in players))

    return players, ship_done, max_single, max_total


# ---------------------------------------------------------------------------
# ПРОГОН И АНАЛИЗ
# ---------------------------------------------------------------------------

def run_batch(profiles, n=6000):
    totals = defaultdict(list)
    wins = defaultdict(float)
    ship_completions = 0
    max_single_overall = 0
    max_total_overall = 0
    for _ in range(n):
        order = profiles[:]
        random.shuffle(order)
        players, ship_done, max_single, max_total = run_game(order)
        max_single_overall = max(max_single_overall, max_single)
        max_total_overall = max(max_total_overall, max_total)
        if ship_done:
            ship_completions += 1
        best_money = max(p.money for p in players)
        money_tied = [p for p in players if p.money == best_money]
        if len(money_tied) > 1:
            # "При равенстве - побеждает тот, кто довёз больше бочек; если и
            # так равно - победа общая" (учитывает обе развязки: взлёт
            # корабля и истечение трёх тактов, т.к. delivered копится весь
            # матч независимо от исхода).
            best_delivered = max(p.delivered for p in money_tied)
            winners = [p for p in money_tied if p.delivered == best_delivered]
        else:
            winners = money_tied
        for w in winners:
            wins[w.profile.label()] += 1.0 / len(winners)
        for p in players:
            totals[p.profile.label()].append(p.money)
    return totals, wins, ship_completions / n, max_single_overall, max_total_overall


GRAND_MAX_SINGLE = 0  # максимум денег у одного игрока за всю историю прогонов
GRAND_MAX_TOTAL = 0   # максимум суммарно денег в игре (у всех игроков разом)


def analyze(label, profiles, n=6000):
    global GRAND_MAX_SINGLE, GRAND_MAX_TOTAL
    totals, wins, ship_rate, max_single, max_total = run_batch(profiles, n)
    GRAND_MAX_SINGLE = max(GRAND_MAX_SINGLE, max_single)
    GRAND_MAX_TOTAL = max(GRAND_MAX_TOTAL, max_total)
    n_players = len(profiles)
    label_counts = defaultdict(int)
    for p in profiles:
        label_counts[p.label()] += 1
    print(f"=== {label} (n={n}, игроков={n_players}) ===")
    notes = []
    for key in sorted(label_counts):
        fair_share = label_counts[key] / n_players
        avg = sum(totals[key]) / len(totals[key])
        share = wins[key] / n
        ratio = share / fair_share if fair_share else 0
        flag = ""
        if ratio > 1.5:
            flag = "  ⚠ заметно сильнее честной доли"
        elif ratio < 0.6:
            flag = "  ⚠ заметно слабее честной доли"
        print(f"  {key:28s} деньги={avg:8.1f}  победы={share:5.1%} (честная доля {fair_share:.1%}){flag}")
        if flag:
            notes.append(f"{key}: {share:.1%} против честных {fair_share:.1%}")
    print(f"  корабль долетел: {ship_rate:5.1%}")
    print(f"  макс. деньги у одного игрока за все прогоны сценария: {max_single}")
    print(f"  макс. денег в игре суммарно за все прогоны сценария: {max_total}")
    if not notes:
        print("  без явных перекосов.")
    print()


# ---------------------------------------------------------------------------
# СТАНДАРТНЫЙ НАБОР СЦЕНАРИЕВ
# ---------------------------------------------------------------------------

BASE_STYLES = ["econ", "aggro", "turtle", "racer"]
EXTENDED_STYLES = ["econ", "aggro", "turtle", "racer", "adaptive", "chaotic", "balanced"]


def cycle(items, n):
    """Повторяет список стилей до длины n (для столов на 5-6 при 4 базовых стилях)."""
    return [items[i % len(items)] for i in range(n)]


def human(style):
    return Profile(style, style, consistency=0.7, attention=0.6, memory=0.6, random_spread=0.2)


def chaotic_player(name="хаотичный"):
    """Хаотичный игрок. consistency/attention, указанные здесь, не используются
    напрямую для решений (Player.__init__ каждую партию тянет их заново из
    [0, CHAOTIC_MAX_LEVEL]) - оставлены на 1.0 только чтобы .label() не
    цеплял бессмысленный для этого стиля суффикс "(согл=..., вним=...)"."""
    return Profile(name, "chaotic")


def make_profile(style, ideal):
    if style == "adaptive":
        if ideal:
            return Profile("адаптивный", "adaptive", 1.0, 1.0)
        return Profile("адаптивный", "adaptive", 0.8, 0.7, memory=0.7, random_spread=0.2)
    if style == "chaotic":
        return chaotic_player()
    return Profile(style, style, 1.0, 1.0) if ideal else human(style)


def natural_table(n_players, ideal):
    """Стол БЕЗ искусственного дублирования стилей - до 6 разных архетипов.
    Дублирование (cycle) на 5-6 игроках специально утяжеляет агрессивные
    стили и занижает гонщика неестественно - это стоит держать как отдельный
    стресс-тест, а не как основной "смешанный стол"."""
    styles = EXTENDED_STYLES[:n_players]
    return [make_profile(s, ideal) for s in styles]


def scenario_suite(quick=False, player_counts=(4, 5, 6)):
    n = 3000 if quick else 8000

    for n_players in player_counts:
        heading = f"########## СТОЛ НА {n_players} ИГРОКОВ ##########"
        print(f"\n{heading}\n")

        # 1. Идеализированные боты (для сверки с прежними прогонами) -------
        for style in BASE_STYLES:
            profiles = [Profile(style, style, 1.0, 1.0) for _ in range(n_players)]
            analyze(f"[{n_players}и] Идеальные боты: все играют «{style}»", profiles, n)

        mix_ideal = natural_table(n_players, ideal=True)
        analyze(f"[{n_players}и] Идеальные боты: смешанный стол (без дублей стилей)", mix_ideal, n)

        if n_players > 4:
            mix_ideal_dup = [Profile(s, s, 1.0, 1.0) for s in cycle(BASE_STYLES, n_players)]
            analyze(f"[{n_players}и] Идеальные боты: смешанный стол "
                    f"(стресс-тест с дублями агрессивных стилей)", mix_ideal_dup, n)

        # 2. То же самое, но приближено к живым людям (не идеальны) --------
        for style in BASE_STYLES:
            profiles = [human(style) for _ in range(n_players)]
            analyze(f"[{n_players}и] Живые игроки: все играют «{style}»", profiles, n)

        mix_human = natural_table(n_players, ideal=False)
        analyze(f"[{n_players}и] Живые игроки: смешанный стол (без дублей стилей)", mix_human, n)

        if n_players > 4:
            mix_human_dup = [human(s) for s in cycle(BASE_STYLES, n_players)]
            analyze(f"[{n_players}и] Живые игроки: смешанный стол "
                    f"(стресс-тест с дублями агрессивных стилей)", mix_human_dup, n)

        # 3. Адаптивные и хаотичные игроки ----------------------------------
        adaptive_table = [make_profile("adaptive", ideal=False) for _ in range(n_players)]
        analyze(f"[{n_players}и] Все играют адаптивно (реагируют на ситуацию)", adaptive_table, n)

        chaotic_table = [chaotic_player() for _ in range(n_players)]
        analyze(f"[{n_players}и] Все играют хаотично (низкое мастерство)", chaotic_table, n)

        realistic_base = [human("econ"), human("aggro"),
                           make_profile("adaptive", ideal=False),
                           chaotic_player()]
        mixed_realistic = cycle(realistic_base, n_players)
        analyze(f"[{n_players}и] Реалистичный смешанный стол (эконом+агрессор+адаптивный+хаотичный)",
                mixed_realistic, n)

        # 4. Спектр внимательности: один игрок скользит от 0 до 1 ----------
        for att in [0.0, 0.25, 0.5, 0.75, 1.0]:
            profiles = [Profile("aggro-опытный", "aggro", 0.8, 1.0) for _ in range(n_players - 1)] + \
                       [Profile(f"aggro-вним{att:.2f}", "aggro", 0.8, att)]
            analyze(f"[{n_players}и] Спектр внимательности: {n_players - 1} опытных aggro "
                    f"+ 1 aggro с вниманием {att:.2f}", profiles, n)

        # 5. Спектр согласованности (последовательности игры) --------------
        for cons in [0.0, 0.25, 0.5, 0.75, 1.0]:
            profiles = [Profile("turtle-опытный", "turtle", 1.0, 0.8) for _ in range(n_players - 1)] + \
                       [Profile(f"turtle-согл{cons:.2f}", "turtle", cons, 0.8)]
            analyze(f"[{n_players}и] Спектр согласованности: {n_players - 1} опытных turtle "
                    f"+ 1 с согласованностью {cons:.2f}", profiles, n)


# ---------------------------------------------------------------------------
# ПОПУЛЯЦИОННОЕ ИССЛЕДОВАНИЕ
# ---------------------------------------------------------------------------
# В отличие от scenario_suite (заранее выбранные, контролируемые составы
# столов - удобно для прицельных A/B-сравнений), здесь столы и параметры
# игроков КАЖДЫЙ РАЗ случайны: случайный размер стола, случайный стиль на
# каждое место, и у "человеческих" стилей ещё и случайные consistency/
# attention/memory внутри своего диапазона. Копим по игроку-партии сырую
# строку и уже ПОСЛЕ прогона ищем зависимости статистически - так виднее
# реальный вклад каждого параметра, не привязанный к тому, какие именно
# сочетания мы заранее додумались проверить руками.

# Именованные расклады стола для популяционных прогонов - по умолчанию все
# стили равновероятны ("uniform"), но реальный стол редко выглядит так: живые
# игроки чаще всего играют "разумно-смешанно", а не чистым архетипом. Каждый
# расклад - вес стиля (не обязательно проценты, нормируются сами).
STYLE_MIXES = {
    "uniform": {s: 1 for s in EXTENDED_STYLES},
    # "уравновешенные" - больше половины стола (см. обсуждение): вес
    # balanced в 12 раз выше веса любого другого стиля по отдельности ->
    # 12 / (12 + 6*1) = 66.7% стола.
    "balanced_majority": {**{s: 1 for s in EXTENDED_STYLES}, "balanced": 12},
    # Мягче: уравновешенные - простое большинство (>50%), но не подавляющее.
    "balanced_slight": {**{s: 1 for s in EXTENDED_STYLES}, "balanced": 7},
}


def random_table(n_players, mix="uniform"):
    weights_by_style = STYLE_MIXES[mix] if isinstance(mix, str) else mix
    styles = list(weights_by_style)
    weights = [weights_by_style[s] for s in styles]
    return [make_profile(random.choices(styles, weights=weights)[0], ideal=False) for _ in range(n_players)]


def run_population(n_players, n_games=20000, mix="uniform"):
    """Размер стола ФИКСИРОВАН на весь прогон - разные размеры стола могут
    иметь разные оптимальные параметры (см. находку про "черепаху" на 3
    игроках), смешивать их в одну статистику не стоит."""
    rows = []
    for _ in range(n_games):
        profiles = random_table(n_players, mix)
        players, ship_done, _, _ = run_game(profiles)
        best_money = max(p.money for p in players)
        money_tied = [p for p in players if p.money == best_money]
        if len(money_tied) > 1:
            best_delivered = max(p.delivered for p in money_tied)
            winners = {p.pid for p in money_tied if p.delivered == best_delivered}
        else:
            winners = {money_tied[0].pid}
        for p in players:
            is_winner = p.pid in winners
            rows.append(dict(
                style=p.profile.style,
                consistency=p.consistency,
                attention=p.attention,
                memory=p.memory,
                money=p.money,
                won=(1.0 / len(winners)) if is_winner else 0.0,
                delivered=p.delivered,
                ship_done=ship_done,
                is_finisher=p.is_finisher,
                is_money_winner=is_winner,
            ))
    return rows


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def _corr(xs, ys):
    xs, ys = list(xs), list(ys)
    if len(xs) < 2:
        return float("nan")
    mx, my = _mean(xs), _mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return float("nan")
    return cov / (vx ** 0.5 * vy ** 0.5)


def report_population(rows, n_players, mix="uniform"):
    print(f"########## ПОПУЛЯЦИОННОЕ ИССЛЕДОВАНИЕ: {n_players} ИГРОКОВ, "
          f"расклад «{mix}», {len(rows)} игроко-партий ##########\n")

    n_games = len(rows) // n_players
    finished_games = sum(1 for r in rows if r["ship_done"] and r["is_finisher"])
    finisher_also_winner = sum(1 for r in rows if r["is_finisher"] and r["is_money_winner"])
    print(f"-- Довёзший решающую бочку побеждает по деньгам? --")
    if finished_games:
        print(f"  Корабль долетел: {finished_games}/{n_games} партий "
              f"({finished_games/n_games:.1%})")
        print(f"  Из них финишер оказался и победителем по деньгам: "
              f"{finisher_also_winner}/{finished_games} ({finisher_also_winner/finished_games:.1%})")
    else:
        print("  Корабль ни разу не долетел в этой выборке.")
    print()

    by_style = defaultdict(list)
    for r in rows:
        by_style[r["style"]].append(r)

    print("-- По стилю (усреднено по всем случайным столам и параметрам) --")
    for style in sorted(by_style):
        rs = by_style[style]
        print(f"  {style:10s} n={len(rs):6d}  деньги={_mean(r['money'] for r in rs):8.1f}  "
              f"победы={_mean(r['won'] for r in rs):6.1%}  "
              f"корабль долетел={_mean(r['ship_done'] for r in rs):5.1%}")
    print()

    print("-- Корреляция параметра с деньгами / с победой, отдельно по стилю --")
    print("   (от -1 до +1; около 0 - параметр практически не влияет)")
    for style in sorted(by_style):
        rs = by_style[style]
        for param in ("consistency", "attention", "memory"):
            xs = [r[param] for r in rs]
            print(f"  {style:10s} {param:12s} "
                  f"corr(деньги)={_corr(xs, (r['money'] for r in rs)):+.3f}  "
                  f"corr(победа)={_corr(xs, (r['won'] for r in rs)):+.3f}")
        print()

    print("-- По каждому параметру: деньги/победы по трети диапазона (низкая/средняя/высокая), по стилю --")
    for style in sorted(by_style):
        rs = by_style[style]
        for param in ("consistency", "attention", "memory"):
            vals = sorted(r[param] for r in rs)
            if len(vals) < 3:
                continue
            lo_cut = vals[len(vals) // 3]
            hi_cut = vals[2 * len(vals) // 3]
            buckets = {"низк.": [], "сред.": [], "выс.": []}
            for r in rs:
                v = r[param]
                key = "низк." if v <= lo_cut else ("выс." if v >= hi_cut else "сред.")
                buckets[key].append(r)
            parts = []
            for key in ("низк.", "сред.", "выс."):
                b = buckets[key]
                if b:
                    parts.append(f"{key} n={len(b)} деньги={_mean(r['money'] for r in b):7.1f} "
                                  f"победы={_mean(r['won'] for r in b):5.1%}")
            print(f"  {style:10s} {param:12s} " + " | ".join(parts))
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="меньше партий на сценарий, быстрее")
    parser.add_argument("--players", type=int, choices=[3, 4, 5, 6], default=None,
                         help="прогнать только один размер стола вместо 3-6")
    parser.add_argument("--population", type=int, default=None, metavar="N",
                         help="вместо scenario_suite - прогнать N партий на полностью "
                              "случайных столах (случайный размер, стиль, параметры) "
                              "и искать зависимости статистически")
    parser.add_argument("--mix", choices=sorted(STYLE_MIXES), default="uniform",
                         help="расклад стилей за столом для --population (по умолчанию "
                              "все стили равновероятны)")
    args = parser.parse_args()
    print(f"Режим разрешения фаз: {RESOLUTION_MODE}\n")

    counts = (args.players,) if args.players else (3, 4, 5, 6)

    if args.population:
        for n_players in counts:
            rows = run_population(n_players, args.population, mix=args.mix)
            report_population(rows, n_players, mix=args.mix)
        return

    scenario_suite(quick=args.quick, player_counts=counts)
    print("########## ИТОГ ПО ВСЕМ ПРОГОНАМ ##########\n")
    print(f"Максимум денег у одного игрока за всю сессию: {GRAND_MAX_SINGLE}")
    print(f"Максимум денег в игре суммарно (все игроки разом) за всю сессию: {GRAND_MAX_TOTAL}")


if __name__ == "__main__":
    main()
