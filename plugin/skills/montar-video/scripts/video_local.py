"""Rota local do montar-video: batida da música e render do MP4 com ffmpeg.

Só biblioteca padrão do Python; precisa do ffmpeg no PATH.

    py -B -I video_local.py batidas musica.m4a        (Windows; python3 no macOS/Linux)
    py -B -I video_local.py musica musica.m4a 15     (confere a música antes do plano)
    py -B -I video_local.py render plano.json
    py -B -I video_local.py teste
"""
import array
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import wave

SR = 11025          # taxa de análise; sobra para achar bumbo e caixa
HOP = 128           # ~11.6 ms por quadro de envelope
FPS = 30
W, H = 1080, 1920
RECEITAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "receitas")


def _ffmpeg(args, **kw):
    return subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", *args], check=True, **kw)


def _amostras(caminho, inicio=0.0, dur=60.0, filtro=None):
    out = _ffmpeg(["-ss", str(inicio), "-t", str(dur), "-i", caminho, "-vn", *(["-af", filtro] if filtro else []),
                   "-ac", "1", "-ar", str(SR),
                   "-f", "s16le", "-"], capture_output=True).stdout
    a = array.array("h")
    a.frombytes(out[: len(out) // 2 * 2])
    if sys.byteorder == "big":
        a.byteswap()
    return a


def _envelope(a, hop=HOP):
    """Fluxo de energia (log) por quadro, só subidas: marca onde a música 'bate'."""
    env, prev = [], None
    for i in range(0, len(a) - hop, hop):
        e = math.log1p(sum(x * x for x in a[i:i + hop]) / hop)
        env.append(max(0.0, e - (e if prev is None else prev)))  # sem golpe falso no primeiro quadro
        prev = e
    m = sum(env) / max(1, len(env))
    env = [max(0.0, x - m) for x in env]
    # suaviza 3 quadros para o pico não cair entre dois pontos da grade de fase
    return [0.5 * env[max(0, i - 1)] + env[i] + 0.5 * env[min(len(env) - 1, i + 1)] for i in range(len(env))]


def _pontua(env, periodo, fase):
    s, n, t = 0.0, 0, fase
    while t < len(env) - 1:
        i = int(t)
        fr = t - i
        s += env[i] * (1 - fr) + env[i + 1] * fr
        n += 1
        t += periodo
    return s / max(1, n)


def _picos(env, qps, piso=0.15):
    """Picos do envelope (máximo local em ±80 ms) com força 0..1 relativa ao percentil 95 dos picos
    da própria faixa (um pico isolado não achata os outros)."""
    w = int(0.08 * qps)
    picos = [i for i in range(len(env)) if env[i] > 0 and env[i] == max(env[max(0, i - w):i + w + 1])]
    alt = sorted(env[i] for i in picos) or [1.0]
    teto = alt[int(0.95 * (len(alt) - 1))] or 1.0
    return [[round(i / qps, 4), round(min(1.0, env[i] / teto), 3)] for i in picos if env[i] >= piso * teto]


def graves(caminho, inicio=0.0, dur=60.0):
    """Golpes do grave (bumbo e baixo, abaixo de 150 Hz): onde a troca de clipe soa na música.
    Fluxo de energia em log, mas com piso na energia grave típica da faixa: abaixo dele (o vazamento
    grave da caixa e do chimbal) a subida conta pouco, senão o log a igualaria a um bumbo.
    Quadro de 5,8 ms para o ataque cair no quadro certo."""
    hop = HOP // 2
    a = _amostras(caminho, inicio, dur, "lowpass=f=150,lowpass=f=150")
    en = [sum(x * x for x in a[i:i + hop]) / hop for i in range(0, len(a) - hop, hop)]
    ref = 0.5 * (sorted(en)[len(en) // 2] or 1.0)  # metade da energia grave mediana da faixa
    lg = [math.log1p(e / ref) for e in en]
    env = [0.0] + [max(0.0, lg[i] - lg[i - 1]) for i in range(1, len(lg))]
    env = [0.5 * env[max(0, i - 1)] + env[i] + 0.5 * env[min(len(env) - 1, i + 1)] for i in range(len(env))]
    return _picos(env, SR / hop)


def batidas(caminho, inicio=0.0, dur=60.0, bpm_min=70, bpm_max=180):
    """Devolve {bpm, primeira, batidas[], golpes[], graves[]} em segundos a partir de `inicio`.

    shortcut: assume tempo constante (vale para trend pop/funk/eletrônico); para faixa com
    tempo variável, trocar por rastreamento batida a batida."""
    env = _envelope(_amostras(caminho, inicio, dur))
    if len(env) < 200:
        raise SystemExit("áudio curto demais para medir a batida (mínimo ~3 s)")
    qps = SR / HOP
    melhor = None
    # varredura grossa de BPM com preferência leve por ~120 (evita dobrar/meio tempo)
    for dbpm in range(bpm_min * 2, bpm_max * 2 + 1):
        bpm = dbpm / 2
        periodo = qps * 60 / bpm
        fases = [float(f) for f in range(int(periodo) + 1)]
        sc, fase = max((_pontua(env, periodo, f), f) for f in fases)
        sc *= math.exp(-0.5 * (math.log2(bpm / 120) / 0.9) ** 2)
        if not melhor or sc > melhor[0]:
            melhor = (sc, bpm, fase)
    _, bpm, fase = melhor
    # refino fino de BPM e fase
    for passo_bpm, passos_fase in ((0.1, 48), (0.02, 96)):
        base_bpm = bpm
        cand = []
        for k in range(-10, 11):
            b = base_bpm + k * passo_bpm
            periodo = qps * 60 / b
            cand.append(max((_pontua(env, periodo, f * periodo / passos_fase), b, f * periodo / passos_fase)
                            for f in range(passos_fase)))
        _, bpm, fase = max(cand)
    periodo_s = 60 / bpm
    primeira = fase / qps
    total = len(env) / qps
    lista = [round(primeira + k * periodo_s, 4) for k in range(int((total - primeira) / periodo_s) + 1)]
    # força de cada meia batida (pico do envelope em ±2 quadros), 0..1: onde a música "bate forte"
    forcas, k = [], 0
    while True:
        q = (primeira + k * periodo_s / 2) * qps
        if q >= len(env) - 1:
            break
        i = int(round(q))
        forcas.append(max(env[max(0, i - 2):i + 3]))
        k += 1
    topo = max(forcas) or 1.0
    return {"bpm": round(bpm, 2), "primeira": round(primeira, 4), "batidas": lista,
            "forca_meias": [round(f / topo, 3) for f in forcas], "golpes": _picos(env, qps),
            "graves": graves(caminho, inicio, dur)}


def _inicio_musica(marcas, piso, vao, sobra, primeira):
    """Onde a música começa no vídeo: o primeiro golpe forte (acima de `piso`, o mesmo que ganha corte) seguido
    de outros sem vão maior que `vao` nos 4 s seguintes, ou seja, onde a batida já está em sequência. Pula
    introdução, voz e efeito sonoro solto (áudio tirado de um vídeo já editado traz os dele). Só vale início que
    deixe música para o vídeo inteiro (até `sobra`). Devolve (início, onde a sequência começa de fato ou None)."""
    fortes = [g for g, f in marcas if f >= piso]

    def em_sequencia(g):
        seg = [x for x in fortes if g <= x <= g + 4.0]
        return len(seg) >= 3 and all(b - a <= vao for a, b in zip(seg, seg[1:])) and seg[-1] >= g + 4.0 - vao
    cabe = [g for g in fortes if g <= sobra]
    inicio = next((g for g in cabe if em_sequencia(g)), cabe[0] if cabe else primeira)
    return inicio, next((g for g in fortes if em_sequencia(g)), None)


def conferir_musica(musica, p):
    """A música antes do plano: BPM, se corta no grave ou nos golpes do som todo, onde o vídeo começa e se a
    faixa serve. `p` é a receita com o plano (usa `duracao`, `musica_inicio`, `golpe_piso`, `corte_max`)."""
    auto = p.get("musica_inicio") in (None, "auto")
    analise = 0.0 if auto else float(p["musica_inicio"])
    total, dur = _duracao(musica), float(p.get("duracao", 15))
    info = batidas(musica, analise, 90)
    piso, vao = float(p.get("golpe_piso", 0.6)), float(p.get("corte_max", 2.5))
    # corta no grave (bumbo e baixo); faixa sem grave que bata (voz, violão) corta nos golpes do som todo
    ouvido = min(90.0, total - analise)
    corte_no = "grave" if sum(1 for _, f in info["graves"] if f >= piso) >= ouvido / vao / 2 else "golpe"
    marcas = info["graves"] if corte_no == "grave" else info["golpes"]
    avisos, seq = [], None
    if auto:
        inicio, seq = _inicio_musica(marcas, piso, vao, total - dur, info["primeira"])
        if seq is not None and seq > inicio + vao:
            avisos.append(f"a batida em sequência só começa em {seq:.1f} s da música e dura {total - seq:.1f} s; para "
                          f"{dur:g} s o vídeo abre com {seq - inicio:.1f} s de introdução da faixa (voz ou efeito sonoro "
                          "de outra edição). Peça a música completa ou um vídeo mais curto")
    else:
        inicio = info["primeira"]  # trecho pedido: começa na primeira batida depois dele
    if total - (analise + inicio) < dur - 0.05:
        avisos.append(f"a música acaba {dur - (total - analise - inicio):.1f} s antes do vídeo; o final fica sem som")
    return {"bpm": info["bpm"], "corte_no": corte_no, "inicio": round(analise + inicio, 3),
            "batida_em_sequencia": None if seq is None else round(seq, 2), "duracao_musica": round(total, 2),
            "pronta": not avisos, "avisos": avisos, "info": info, "marcas": marcas, "analise": analise}


def _receita(plano):
    """Junta a receita (template nosso) com o plano; blocos do plano sobrescrevem os da receita pelo índice."""
    base = {}
    if plano.get("receita"):
        with open(os.path.join(RECEITAS, plano["receita"] + ".json"), encoding="utf-8") as f:
            base = json.load(f)
    p = {**base, **plano}
    if "blocos" in base and "blocos" in plano:
        p["blocos"] = [{**(base["blocos"][i] if i < len(base["blocos"]) else {}), **b}
                       for i, b in enumerate(plano["blocos"])]
    if "blocos" not in p:  # forma curta: só uma lista de clipes em tela cheia
        p["blocos"] = [{"layout": "cheio", "paineis": [p.get("clipes", [])]}]
    return p


def _duracao(arquivo):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", arquivo],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def _quadro(t):
    return round(t * FPS) / FPS


def _paineis(bloco, p):
    """Retângulos (x, y, w, h) de cada painel do layout, em pixels pares."""
    lay, m = bloco.get("layout", "cheio"), int(bloco.get("margem", p.get("margem", 0)))
    par = lambda v: int(v) // 2 * 2
    if lay == "cheio":
        return [(0, 0, W, H)]
    if lay in ("cima-baixo", "faixas"):
        n = 2 if lay == "cima-baixo" else int(bloco.get("n", len(bloco.get("paineis", [])) or 2))
        h = par((H - (n + 1) * m) / n)
        return [(m, m + i * (h + m), par(W - 2 * m), h) for i in range(n)]
    if lay == "lado-a-lado":
        m = m or 40
        w = par((W - 3 * m) / 2)
        h = par(min(H - 2 * m, w * 16 / 9))
        y = par((H - h) / 2)
        return [(m, y, w, h), (2 * m + w, y, w, h)]
    raise SystemExit(f"layout desconhecido: {lay}")


def _fronteiras(golpes, ini, dur, p, abertura):
    """Onde cortar dentro de [ini, ini+dur], seguindo a música e não uma grade de BPM: os golpes do grave
    (bumbo e baixo) acima de `golpe_piso` (relativo aos golpes fortes desta faixa), do mais forte para o mais
    fraco, com pelo menos `corte_min` entre cortes. Onde o grave bate forte e junto, os clipes ficam curtos;
    onde ele some, ficam longos. Vão maior que `corte_max` ganha o golpe mais forte do meio dele (nunca um
    corte no silêncio). Na abertura, o gancho termina no golpe mais forte entre `gancho_min` e `gancho_max`."""
    cmin, cmax = p.get("corte_min", 0.45), p.get("corte_max", 2.5)
    fim = ini + dur
    todos = [g for g in golpes if ini + cmin <= g[0] <= fim - cmin]
    dentro = [g for g in todos if g[1] >= p.get("golpe_piso", 0.6)]
    aceitos = []
    if abertura:
        gancho = [g for g in dentro if ini + p.get("gancho_min", 1.5) <= g[0] <= ini + p.get("gancho_max", 4.0)]
        if gancho:
            aceitos.append(max(gancho, key=lambda g: (g[1], -g[0])))
    for g in sorted(dentro, key=lambda g: -g[1]):
        if abertura and aceitos and g[0] < aceitos[0][0]:
            continue  # nada corta o gancho
        if all(abs(g[0] - a[0]) >= cmin for a in aceitos):
            aceitos.append(g)
    tempos = sorted(a[0] for a in aceitos)
    mudou = True
    while mudou:  # clipe acima de corte_max ganha o golpe mais forte do vão; sem golpe, fica longo (não corta no silêncio)
        mudou = False
        bordas = [ini] + tempos + [fim]
        for a, b in zip(bordas, bordas[1:]):
            limite = p.get("gancho_max", 4.0) if abertura and a == ini and tempos else cmax  # o gancho pode ser longo
            meio = [g for g in todos if a + cmin <= g[0] <= b - cmin and g[1] >= 0.3] if b - a > limite else []
            if meio:
                tempos.append(max(meio, key=lambda g: g[1])[0])
                tempos.sort()
                mudou = True
                break
    return [t for t in tempos if ini < t < fim]


def _cortes(clipes, p, grade, total, t0=0.0, golpes=None, abertura=True):
    """Tempos (início, fim) de cada clipe no painel, relativos ao bloco.

    Com golpes e `cortar_nos_golpes`, as fronteiras vêm de `_fronteiras`; sem, da grade de batidas
    (`batidas_por_corte`) ou de segundos."""
    if not clipes:
        return []
    if any(c.get("continuo") for c in clipes[:1]) or len(clipes) == 1:  # quem fala, ou painel de um clipe só
        return [(clipes[0], 0.0, _quadro(total))]
    if golpes and p.get("cortar_nos_golpes") and not any(c.get("batidas") for c in clipes):
        bordas = [0.0] + [_quadro(t - t0) for t in _fronteiras(golpes, t0, total, p, abertura)] + [_quadro(total)]
        return [(clipes[k % len(clipes)], a, b) for k, (a, b) in enumerate(zip(bordas, bordas[1:])) if b > a]
    padrao = p.get("batidas_por_corte", 2)
    padrao = padrao if isinstance(padrao, list) else [padrao]
    partes, t, i = [], 0.0, 0
    while t < total - 1e-3:
        c = clipes[i % len(clipes)]
        if grade:
            n = c.get("batidas") or (p.get("gancho_batidas") if i == 0 else None) or padrao[i % len(padrao)]
            n_seg = n * grade
        else:
            n_seg = c.get("segundos", p.get("segundos_por_corte", 1.5))
        fim = _quadro(min(total, t + n_seg))
        if fim <= t:
            break
        partes.append((c, t, fim))
        t, i = fim, i + 1
    return partes


_ANALISE = {}


def _analise(arquivo):
    """Movimento (YDIF) e desfoque por quadro, a 10 qps, em miniatura; guardado por arquivo."""
    if arquivo not in _ANALISE:
        out = subprocess.run(["ffmpeg", "-v", "error", "-i", arquivo, "-an", "-vf",
                              "fps=10,scale=96:-2,signalstats,blurdetect,metadata=print:file=-", "-f", "null", "-"],
                             capture_output=True, text=True).stdout
        quadros, atual = [], None
        for linha in out.splitlines():
            if "pts_time:" in linha:
                atual = [float(linha.split("pts_time:")[1].split()[0]), 0.0, 0.0]
                quadros.append(atual)
            elif atual and "YDIF=" in linha:
                atual[1] = float(linha.split("=")[1])
            elif atual and "lavfi.blur=" in linha:
                atual[2] = float(linha.split("=")[1])
        _ANALISE[arquivo] = quadros
    return _ANALISE[arquivo]


_RASTRO = {}
RW = 54  # largura da miniatura do rastro; ~5 mil pontos por quadro bastam para achar o produto


def _rastro(arquivo):
    """Onde está o produto em cada quadro (5 qps): centro e largura em fração do quadro, ou None.
    Produto = o que destoa do fundo (fundo medido por linha, porque chão, parede e mesa têm gradiente),
    tirando tom de pele (a mão que segura não é o assunto). Mais de 30% do quadro destoando é cena
    (pessoa, loja): não há produto a enquadrar."""
    if arquivo not in _RASTRO:
        nums = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                               "stream=width,height:stream_side_data=rotation", "-of", "csv=p=0", arquivo],
                              capture_output=True, text=True, check=True).stdout.replace("\n", ",").split(",")
        nums = [int(float(x)) for x in nums if x.strip()]
        sw, sh = nums[:2]
        if any(abs(r) in (90, 270) for r in nums[2:]):  # o ffmpeg gira o quadro; as medidas giram junto
            sw, sh = sh, sw
        rh = max(2, round(RW * sh / sw / 2) * 2)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", arquivo, "-an", "-vf", f"fps=5,scale={RW}:{rh}",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        n, quadros = RW * rh * 3, []
        for i in range(0, len(raw) - n + 1, n):
            q = raw[i:i + n]
            ys, cbs, crs = [], [], []
            for j in range(0, n, 3):
                y = 0.299 * q[j] + 0.587 * q[j + 1] + 0.114 * q[j + 2]
                ys.append(y); cbs.append((q[j + 2] - y) * 0.564); crs.append((q[j] - y) * 0.713)
            fy = [sorted(ys[r * RW:(r + 1) * RW])[RW // 2] for r in range(rh)]
            fcb, fcr = sorted(cbs)[len(cbs) // 2], sorted(crs)[len(crs) // 2]
            xs, yy = [], []
            for k in range(RW * rh):
                cb, cr = cbs[k] - fcb, crs[k] - fcr
                if cr > 6 and cr > -cb and cb <= 2:  # tom quente: mão
                    continue
                d = ys[k] - fy[k // RW]
                if max(0, -d) + 0.5 * max(0, d) + 2.5 * (abs(cb) + abs(cr)) > 50:
                    xs.append(k % RW); yy.append(k // RW)
            caixa = None
            if 12 <= len(xs) <= 0.3 * RW * rh:
                borda = sum(1 for x, y in zip(xs, yy) if x < 2 or x >= RW - 2 or y < 2)  # antes de ordenar
                xs.sort(); yy.sort()
                pc = lambda a, f: a[int(f * (len(a) - 1))]
                # o último campo diz se o produto encosta na lateral ou no topo: cortado ou perto demais
                caixa = ((pc(xs, .5) + .5) / RW, (pc(yy, .5) + .5) / rh, (pc(xs, .9) - pc(xs, .1) + 1) / RW, borda >= 3)
            quadros.append((len(quadros) / 5, caixa))
        _RASTRO[arquivo] = (sw, sh, quadros)
    return _RASTRO[arquivo]


def _enquadre(arquivo, origem, fonte, w, h, alvo, teto):
    """Recorte que segue o produto: zoom fixo no clipe (entre 1 e `teto`) para a largura dele chegar a
    `alvo` do painel e para caber pô-lo no centro; centro suavizado (~1 s) em quadros-chave a cada 0,4 s.
    None: não há produto."""
    sw, sh, q = _rastro(arquivo)
    jan = [(t - origem, c) for t, c in q if origem - 0.6 <= t <= origem + fonte + 0.6]
    vistos = [c for _, c in jan if c]
    if len(vistos) < max(2, 0.5 * len(jan)):
        return None
    cw, ch = (sh * w / h, sh) if sw / sh > w / h else (sw, sw * h / w)  # recorte de cobertura do painel
    med = lambda k: sorted(c[k] for c in vistos)[len(vistos) // 2]
    z_tam = cw * alvo / (med(2) * sw)
    # zoom que dá folga para pôr o produto no centro (o recorte de cobertura já pode andar no eixo que sobra)
    z_centro = max(cw / max(sw * 0.5, sw - 2 * abs(med(0) - 0.5) * sw), ch / max(sh * 0.5, sh - 2 * abs(med(1) - 0.5) * sh))
    z = max(1.0, min(teto, max(z_tam, z_centro)))
    cw, ch = int(cw / z) // 2 * 2, int(ch / z) // 2 * 2
    pts, ult = [], vistos[0]
    for t, c in jan:
        ult = c or ult
        pts.append((t, ult[0] * sw, ult[1] * sh))
    suave = lambda i, k: sum(p[k] for p in pts[max(0, i - 2):i + 3]) / len(pts[max(0, i - 2):i + 3])
    chaves, t = [], 0.0
    while True:
        i = min(range(len(pts)), key=lambda j: abs(pts[j][0] - t))
        chaves.append((t, max(0, min(sw - cw, suave(i, 1) - cw / 2)), max(0, min(sh - ch, suave(i, 2) - ch / 2))))
        if t >= fonte:
            break
        t = min(fonte, t + 0.4)

    def expr(k):
        e = f"{chaves[-1][k]:.1f}"
        for (t0, *a), (t1, *b) in reversed(list(zip(chaves, chaves[1:]))):
            e = f"if(lt(t,{t1:.2f}),{a[k - 1]:.1f}+({b[k - 1] - a[k - 1]:.1f})*(t-{t0:.2f})/{t1 - t0:.2f},{e})"
        return e
    return f"crop={cw}:{ch}:x='{expr(1)}':y='{expr(2)}'", z


def _nota_enquadre(arquivo, ini, dur, alvo, teto):
    """0 a 1: fração da janela com o produto perto do centro e do tamanho `alvo` (o que o zoom
    sozinho não conserta: produto perto demais da câmera ou encostado na borda)."""
    _, _, q = _rastro(arquivo)
    jan = [c for t, c in q if ini <= t < ini + dur] or [None]
    return sum(1 for c in jan if c and abs(c[2] - alvo) <= 0.15 and abs(c[0] - 0.5) <= 0.12
               and abs(c[1] - 0.5) <= 0.1 and not c[3]) / len(jan)


def _melhor_trecho(arquivo, dur, ocupados=(), enquadre=None):
    """Início da janela mais viva e nítida do bruto, fora do começo e do fim (mão entrando, tremido)
    e sem repetir trechos já usados. Movimento acima do percentil 90 conta como 90 (chacoalhão não vale mais).
    Com `enquadre` (alvo, teto), pesa também o produto num tamanho enquadrável; bruto sem produto (pessoa,
    loja) prefere a janela em que a ação acontece e termina parada, para não cortar antes do gesto concluído."""
    q = _analise(arquivo)
    if not q:
        return 0.0
    total = q[-1][0]
    mov = sorted(x[1] for x in q)
    teto = mov[int(0.9 * (len(mov) - 1))] or 1.0
    borr = sorted(x[2] for x in q)
    mediana_b = borr[len(borr) // 2] or 1.0
    margem = min(0.4, max(0.0, (total - dur) / 2))
    melhor = (None, 0.0)
    pose = enquadre and sum(1 for _, c in _rastro(arquivo)[2] if c) < 0.5 * len(_rastro(arquivo)[2])
    s = margem
    while s + dur <= total - margem + 1e-6:
        if all(s + dur <= a or s >= b for a, b in ocupados):
            jan = [x for x in q if s <= x[0] < s + dur] or q[:1]
            nota = sum(min(x[1], teto) for x in jan) / len(jan) / teto - 0.5 * sum(x[2] for x in jan) / len(jan) / mediana_b
            if pose:  # pessoa ou cena: a ação acontece e a janela fecha no gesto concluído (pôs e olhou)
                k = max(1, int(0.7 * len(jan)))
                acao, fim = jan[:k], jan[k:] or jan[-1:]
                nota = (sum(min(x[1], teto) for x in acao) / len(acao) - 1.5 * sum(min(x[1], teto) for x in fim) / len(fim)) / teto \
                    - 0.5 * sum(x[2] for x in jan) / len(jan) / mediana_b
            elif enquadre:
                nota += 3 * _nota_enquadre(arquivo, s, dur, *enquadre)
            if melhor[0] is None or nota > melhor[0]:
                melhor = (nota, s)
        s += 0.1
    return round(melhor[1], 2)


def _assinatura(arquivo, t):
    """Cor média num mosaico 4x4 do quadro em t: serve para medir se dois planos se parecem."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", arquivo, "-frames:v", "1",
                          "-vf", "scale=4:4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return list(raw)


def _ordem_contraste(clipes):
    """Mantém o primeiro (gancho) e encadeia os outros do mais diferente para o mais diferente do anterior."""
    if len(clipes) < 3:
        return clipes
    ass = [_assinatura(c["arquivo"], float(c.get("inicio") or 1.0)) for c in clipes]
    dist = lambda a, b: sum((x - y) ** 2 for x, y in zip(a, b))
    ordem, resto = [0], list(range(1, len(clipes)))
    while resto:
        k = max(resto, key=lambda r: dist(ass[r], ass[ordem[-1]]))
        ordem.append(k)
        resto.remove(k)
    return [clipes[k] for k in ordem]


# Repertório da Vitória (D01) em filtros do ffmpeg. Transição = início do clipe que entra, no golpe.
TRANSICOES = {
    "corte": "",
    "flash": "fade=t=in:st=0:d=0.12:color=white",
    "fade": "fade=t=in:st=0:d=0.2",
    "desfoque": "boxblur=20:2:enable='lt(t,0.13)'",
    "brilho": "eq=brightness=0.18:contrast=1.1:saturation=1.2:enable='lt(t,0.13)'",
    "flash_falha": "rgbashift=rh=24:bh=-24:enable='lt(t,0.1)',fade=t=in:st=0:d=0.08:color=white",
    "zoom_in": "",   # vão no zoompan, abaixo
    "zoom_out": "",
}
EFEITOS = {
    "camera_de_mao": "crop=iw*0.94:ih*0.94:x='(iw-ow)/2+sin(t*11)*iw*0.012':y='(ih-oh)/2+cos(t*8.3)*ih*0.01',scale={w}:{h}",
    "obturador_lento": "tmix=frames=4",
    "cromatico": "rgbashift=rh=-6:bh=6",
    "negativo": "negate=enable='lt(t,0.07)'",
}
SFX = {  # (fonte lavfi, quanto começa antes do corte em s)
    # ganhos medidos para que todos tenham pico perto de -6 dBFS; o mix ajusta cada um à música (`sfx_abaixo_db`)
    "swoosh": ("anoisesrc=d=0.4:c=pink:a=0.6:r=44100,highpass=f=700,lowpass=f=5000,afade=t=in:d=0.28,afade=t=out:st=0.28:d=0.12,volume=9dB", 0.28),
    "pop": ("sine=f=520:d=0.07:sample_rate=44100,afade=t=out:st=0.01:d=0.06,volume=12dB", 0.0),
    "click": ("sine=f=2600:d=0.02:sample_rate=44100,afade=t=out:d=0.02,volume=12dB", 0.0),
    "glitch": ("anoisesrc=d=0.15:a=0.5:r=44100,acrusher=bits=3:samples=30:mix=1", 0.0),
    "vento": ("anoisesrc=d=0.8:c=brown:a=0.5:r=44100,lowpass=f=500,afade=t=in:d=0.4,afade=t=out:st=0.4:d=0.4,volume=6dB", 0.4),
}
SFX.update({"woosh": SFX["swoosh"], "swish": SFX["swoosh"], "shun": SFX["swoosh"]})
SFX_DA_TRANSICAO = {"zoom_in": "swoosh", "zoom_out": "swoosh", "desfoque": "swoosh", "flash_falha": "glitch",
                    "zoom_passagem": "swoosh", "desfoque_passagem": "swoosh", "deslizar": "swoosh", "chicote": "swoosh",
                    "pixel": "glitch", "glitch": "glitch", "queimado": "swoosh"}
SEM_EQUIVALENTE = set()

# Transições entre dois clipes (os dois se sobrepõem; o meio da transição cai no corte): nome -> (xfade, quadros).
# Nativas do ffmpeg, rápidas. "chicote" é uma expressão do xfade-easing (ver XFADE_EASING abaixo), pesada:
# calculada em meia resolução, numa thread só (a expressão guarda valores em st()/ld(), que se embaralham entre
# threads e viram ruído) e no máximo uma por vídeo.
XFADE = {
    "combinar": ("fade", 10),            # Combinar da Vitória (dissolve suave)
    "desfoque_passagem": ("hblur", 8),   # passagem com desfoque horizontal
    "zoom_passagem": ("zoomin", 8),      # passagem com zoom; o mais perto do Radial Blur
    "radial_blur": ("zoomin", 8),
    "deslizar": ("smoothup", 8),
    "pixel": ("pixelize", 8),
    "chicote": ("custom", 8),
}
# xfade-easing, (c) Raymond Luckhurst, licença MIT, https://github.com/scriptituk/xfade-easing (ver TERCEIROS.md):
# easing cubic-in-out + gl-transition DirectionalScaled (empurrão com escala, tipo "whip pan")
XFADE_EASING = ("st(0,if(lt(P,0.5),4*P^3,1-4*(1-P)^3));"
                "st(1,0);st(2,1);st(3,0.7);st(4,0);st(5,1-ld(0));st(3,1-(1-1/ld(3))*sin(ld(5)*PI));"
                "st(5,pow(sin(ld(5)*PI/2),3));st(1,X/W+ld(5)*sgn(ld(1)));st(2,1-Y/H+ld(5)*sgn(ld(2)));"
                "st(5,(mod(ld(1),1)-0.5)*ld(3)+0.5);st(6,(mod(ld(2),1)-0.5)*ld(3)+0.5);"
                "if(between(ld(5),0,1)*between(ld(6),0,1),st(5,ld(5)*W);st(6,(1-ld(6))*H);"
                "if(between(ld(1),0,1)*between(ld(2),0,1),ifnot(PLANE,a0(ld(5),ld(6)),ifnot(1-PLANE,a1(ld(5),ld(6)),"
                "ifnot(2-PLANE,a2(ld(5),ld(6)),a3(ld(5),ld(6))))),ifnot(PLANE,b0(ld(5),ld(6)),ifnot(1-PLANE,b1(ld(5),ld(6)),"
                "ifnot(2-PLANE,b2(ld(5),ld(6)),b3(ld(5),ld(6)))))),ifnot(PLANE,max(ld(4)*255,0),if(3-PLANE,127,gte(ld(4),0)*255)))")
# Efeitos de sobreposição da `visual_pasta` (fundo preto, mistura "tela"): o ponto mais claro cai no corte.
# Sem a pasta, cai no equivalente feito por filtro.
SOBREPOSICOES = {"luz": "brilho", "glitch": "flash_falha", "queimado": "flash"}


def _tempo(dur, vel, rampa):
    """Tempo do bruto usado e o setpts da câmera lenta. Com rampa, entra no golpe em velocidade normal e
    desacelera até `vel` no primeiro terço (velocidade linear no tempo do bruto: saída = ln(1+kT)/k)."""
    if vel >= 1.0:
        return dur, ""
    if not rampa:
        return dur * vel, f"setpts=PTS/{vel}"
    k_saida = math.log(vel) / (vel - 1)        # quanto a rampa dura na saída por segundo de bruto
    a = 0.3 * dur / k_saida                     # rampa ocupa 30% do clipe na saída
    k = (vel - 1) / a
    fim_rampa = math.log(vel) / k
    return a + (dur - fim_rampa) * vel, (f"setpts='if(lt(T,{a:.4f}),log(1+({k:.4f})*T)/({k:.4f}),"
                                          f"{fim_rampa:.4f}+(T-{a:.4f})/{vel})/TB'")


def _sons(pasta, nome):
    """Arquivos de um efeito (som ou sobreposição) no pacote: `pasta/nome/*` (várias versões) ou `pasta/nome.*`."""
    if not pasta:
        return []
    audio = (".wav", ".mp3", ".m4a", ".ogg", ".aac", ".flac", ".mp4", ".mov", ".webm")
    sub = os.path.join(pasta, nome)
    if os.path.isdir(sub):
        return sorted(os.path.join(sub, f) for f in os.listdir(sub) if f.lower().endswith(audio))
    return sorted(os.path.join(pasta, f) for f in os.listdir(pasta) if os.path.splitext(f)[0] == nome and f.lower().endswith(audio))


def _pico_visual(arquivo):
    """Segundo do quadro mais claro de uma sobreposição: é ele que cai no corte."""
    if arquivo not in _PICOS:
        out = subprocess.run(["ffmpeg", "-v", "error", "-i", arquivo, "-an", "-vf",
                              "scale=64:-2,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-", "-f", "null", "-"],
                             capture_output=True, text=True).stdout
        tempos = [float(x.split("pts_time:")[1].split()[0]) for x in out.splitlines() if "pts_time:" in x]
        brilho = [float(x.split("=")[1]) for x in out.splitlines() if "YAVG=" in x]
        _PICOS[arquivo] = tempos[max(range(len(brilho)), key=lambda i: brilho[i])] if brilho else 0.0
    return _PICOS[arquivo]


_PICOS = {}


def _pico(arquivo):
    """Segundo em que o som do arquivo é mais forte (energia em janelas de 20 ms, não a amostra mais alta, que
    num swoosh longo chega antes do que se ouve): é ele que cai no corte."""
    if arquivo not in _PICOS:
        a, h = _amostras(arquivo, 0, 10), int(0.02 * SR)
        en = [sum(x * x for x in a[i:i + h]) for i in range(0, max(1, len(a) - h), h // 2)]
        _PICOS[arquivo] = (max(range(len(en)), key=lambda i: en[i]) * (h // 2) + h / 2) / SR if a else 0.0
    return _PICOS[arquivo]


_NIVEIS = {}


def _nivel_pico(fonte):
    """Nível do trecho mais forte (janela de 20 ms, dBFS) de um arquivo de som ou de uma fonte lavfi."""
    if fonte not in _NIVEIS:
        if os.path.exists(fonte):
            a = _amostras(fonte, 0, 10)
        else:
            a = array.array("h")
            a.frombytes(_ffmpeg(["-f", "lavfi", "-i", fonte, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                                capture_output=True).stdout)
        h = int(0.02 * SR)
        en = max((sum(x * x for x in a[i:i + h]) / h for i in range(0, max(1, len(a) - h), h // 2)), default=0)
        _NIVEIS[fonte] = 10 * math.log10(en / 32768 ** 2 + 1e-12)
    return _NIVEIS[fonte]


def _nivel_musica(musica, t, volume=1.0):
    """Nível médio da música (dBFS) em 0,5 s em volta de `t`, já com o volume dela no mix."""
    a = _amostras(musica, max(0.0, t - 0.25), 0.5)
    en = sum(x * x for x in a) / max(1, len(a))
    return 10 * math.log10(en / 32768 ** 2 + 1e-12) + 20 * math.log10(max(volume, 1e-6))


def _trecho(idx, c, dur, p, w, h, transicao, avisos, pulsos=(), velocidade=1.0, enq=None):
    """Filtro de um clipe: recorte do bruto (seguindo o produto, com `enq`), velocidade com rampa e
    quadros interpolados, zoom com pulsos nos golpes de dentro do clipe, transição de entrada e efeito.
    `dur` já inclui a sobra para as transições entre clipes (`XFADE`)."""
    fonte, lento = _tempo(dur, velocidade, p.get("rampa"))
    origem = float(c.get("inicio", 0))
    disp = _duracao(c["arquivo"])
    origem = max(0.0, min(origem, disp - fonte)) if disp > fonte else 0.0
    enquadra = (enq or {}).get("crop")
    f = f"[{idx}:v]trim=start={origem:.3f}:duration={fonte:.3f},setpts=PTS-STARTPTS,"
    f += f"{enquadra},scale={w}:{h}" if enquadra else f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    if lento:
        # quadros intermediários por fluxo de movimento: câmera lenta lisa a partir de 30 qps;
        # calculados em meia resolução (a interpolação é o passo caro) e depois ampliados
        f += (f",fps={FPS},scale={w // 2 // 2 * 2}:{h // 2 // 2 * 2},minterpolate=fps={math.ceil(FPS / velocidade)}:mi_mode=mci,"
              f"{lento},fps={FPS},scale={w}:{h}")
    else:
        f += f",fps={FPS}"
    f += ",setsar=1"
    if disp < origem + fonte:  # bruto curto: segura o último quadro em vez de cortar o tempo
        f += f",tpad=stop_mode=clone:stop_duration={dur:.3f},trim=duration={dur:.3f}"
    for nome in [transicao] + list(c.get("efeitos") or ([c["efeito"]] if c.get("efeito") else [])):
        if nome in SEM_EQUIVALENTE or (nome not in TRANSICOES and nome not in EFEITOS and nome not in XFADE
                                       and nome not in SOBREPOSICOES):
            avisos.append(f"{os.path.basename(c['arquivo'])}: '{nome}' sem equivalente na rota local, ficou de fora")
    quadros = max(1, round(dur * FPS))
    z = "1"
    if c.get("zoom", p.get("zoom")) and not c.get("continuo"):
        z = f"(1+({float(p.get('zoom_max', 1.08))}-1)*on/{quadros})"
    if transicao == "zoom_in":
        z += "*(1+0.15*min(1,on/6))"
    elif transicao == "zoom_out":
        z += "*(1+0.25*max(0,1-on/6))"
    for a in pulsos:  # golpe dentro do clipe: empurrão de 4% que some em 6 quadros
        q = round(a * FPS)
        z += f"*(1+0.04*gte(on,{q})*max(0,1-(on-{q})/6))"
    if z != "1":
        f += f",zoompan=z='{z}':d=1:x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':s={w}x{h}:fps={FPS}"
    if TRANSICOES.get(transicao):
        f += "," + TRANSICOES[transicao]
    for nome in c.get("efeitos") or ([c["efeito"]] if c.get("efeito") else []):
        if nome in EFEITOS:
            f += "," + EFEITOS[nome].format(w=w, h=h)
    # quadro a quadro exato: a câmera lenta interpolada pode sobrar um quadro, e a sobra acumula atraso na música
    return f + f",tpad=stop_mode=clone:stop_duration=0.2,trim=end_frame={quadros},setpts=PTS-STARTPTS,setsar=1"


def render(plano_path):
    with open(plano_path, encoding="utf-8") as f:
        p = _receita(json.load(f))
    base = os.path.dirname(os.path.abspath(plano_path))
    absol = lambda x: x if os.path.isabs(x) else os.path.join(base, x)
    musica, voz = p.get("musica"), p.get("voz")
    m_ini, grade, info, golpes, corte_no, avisos_musica = 0.0, None, None, None, None, []
    if musica:
        musica = absol(musica)
        if p.get("no_ritmo", True):
            m = conferir_musica(musica, p)
            info, grade, corte_no, m_ini, avisos_musica = m["info"], 60 / m["bpm"], m["corte_no"], m["inicio"], m["avisos"]
            golpes = [[round(g - (m_ini - m["analise"]), 4), f] for g, f in m["marcas"] if g - (m_ini - m["analise"]) > -0.02]
        elif p.get("musica_inicio") not in (None, "auto"):
            m_ini = float(p["musica_inicio"])

    # duração de cada bloco: em batidas (encaixa na música) ou segundos; o último pode preencher até `duracao`
    blocos, t = [], 0.0
    total_pedido = p.get("duracao")
    for i, b in enumerate(p["blocos"]):
        if b.get("batidas") and grade:
            d = b["batidas"] * grade
        elif b.get("segundos"):
            d = float(b["segundos"])
        else:
            d = max(0.0, float(total_pedido or 15) - t)
        if total_pedido:
            d = min(d, float(total_pedido) - t)
        d = _quadro(t + d) - _quadro(t)
        if d <= 0:
            break
        blocos.append((b, _quadro(t), d))
        t = _quadro(t + d)
    total = t

    entradas, filtros, nomes_blocos, n_ent = [], [], [], [0]

    def entra(arquivo, *antes):
        entradas.extend([*antes, "-i", arquivo])
        n_ent[0] += 1
        return n_ent[0] - 1

    flash_modo = p.get("flash_no_corte", "gancho")
    giro = p.get("transicoes") or []
    usou_chicote, sobreposicoes = False, []
    avisos, sfx, cortes_v, usado, escolhas = [], [], set(), {}, []
    avisos.extend(avisos_musica)
    pasta_sfx = absol(p["sfx_pasta"]) if p.get("sfx_pasta") else None
    pasta_visual = absol(p["visual_pasta"]) if p.get("visual_pasta") else None
    if pasta_visual and not os.path.isdir(pasta_visual):
        avisos.append(f"pasta de efeitos visuais não encontrada ({pasta_visual}); usei os feitos por filtro")
        pasta_visual = None
    if pasta_sfx and not os.path.isdir(pasta_sfx):
        avisos.append(f"pasta de efeitos sonoros não encontrada ({pasta_sfx}); usei os sintetizados")
        pasta_sfx = None  # usado: trechos já usados de cada bruto
    for bi, (b, t0, d) in enumerate(blocos):
        rets = _paineis(b, p)
        paineis = b.get("paineis") or []
        if len(paineis) < len(rets):
            raise SystemExit(f"bloco {bi + 1} ({b.get('layout')}) pede {len(rets)} painéis e recebeu {len(paineis)}")
        filtros.append(f"color=c={b.get('fundo', p.get('fundo', 'black'))}:s={W}x{H}:r={FPS}:d={d:.3f}[b{bi}f]")
        ultimo = f"b{bi}f"
        for pi, ((x, y, w, h), clipes) in enumerate(zip(rets, paineis)):
            clipes = [{**c, "arquivo": absol(c["arquivo"])} for c in clipes]
            # quem fala segue a voz: o trecho começa onde a voz está no início do bloco
            for c in clipes:
                if c.get("continuo") and voz and os.path.abspath(c["arquivo"]) == absol(voz["arquivo"]):
                    c["inicio"] = float(voz.get("inicio", 0)) + t0
            nomes = []
            pb = {**p, **b}
            if pb.get("ordem") == "contraste" and not any(c.get("continuo") for c in clipes):
                clipes = _ordem_contraste(clipes)
            partes = _cortes(clipes, pb, grade, d, t0, golpes, bi == 0)
            bordas = {round(t0 + a0, 3) for _, a0, _ in partes}
            # transição de cada corte antes de montar: a do corte seguinte decide quanto o clipe sobra no fim
            transs = []
            for k, (c, a0, a1) in enumerate(partes):
                flash = flash_modo == "todos" or (flash_modo == "gancho" and bi == 0 and pi == 0 and k == 1) \
                    or (flash_modo == "blocos" and k == 0 and bi > 0)
                if "transicao" in c:
                    trans = c["transicao"]
                elif k == 0 and not (bi > 0 and flash):
                    trans = "corte"
                elif flash:
                    trans = pb.get("transicao_gancho", "flash") if flash_modo == "gancho" else "flash"
                else:
                    trans = giro[(k - 1) % len(giro)] if giro else "corte"
                if trans in SOBREPOSICOES and not _sons(pasta_visual, trans):
                    trans = SOBREPOSICOES[trans]  # sem o pacote visual, o equivalente por filtro
                if trans == "chicote" and usou_chicote:
                    trans = "zoom_passagem"  # a expressão é pesada: uma por vídeo
                usou_chicote |= trans == "chicote"
                transs.append(trans)
            quadros = [round((a1 - a0) * FPS) for _, a0, a1 in partes]
            sobre = [XFADE[t][1] if k > 0 and t in XFADE else 0 for k, t in enumerate(transs)] + [0]
            for k in range(len(partes)):  # clipe curto demais para as duas sobreposições: o corte fica seco
                while quadros[k] - (sobre[k] + sobre[k + 1]) // 2 < 4 and (sobre[k] or sobre[k + 1]):
                    m = k + 1 if sobre[k + 1] else k
                    sobre[m], transs[m] = 0, "corte"
            pedacos = []
            for k, (c, a0, a1) in enumerate(partes):
                trans = transs[k]
                antes, depois = sobre[k] // 2 / FPS, sobre[k + 1] // 2 / FPS
                vel = 1.0
                if pb.get("lento") and not c.get("continuo") and a1 - a0 >= pb.get("lento_min", 1.2):
                    vel = float(pb["lento"])  # clipe longo respira em câmera lenta leve
                vel = float(c.get("velocidade", vel))
                dur_total = antes + (a1 - a0) + depois
                fonte = _tempo(dur_total, vel, pb.get("rampa"))[0]
                alvo = (float(pb.get("tamanho_alvo", 0.5)), float(pb.get("zoom_teto", 1.35)))
                enquadrar = pb.get("enquadrar") and c.get("enquadrar", True) and not c.get("continuo")
                if c.get("continuo"):
                    pass
                elif c.get("inicio") in (None, "auto"):  # escolhe a janela mais viva e nítida ainda não usada
                    c = {**c, "inicio": _melhor_trecho(c["arquivo"], fonte, usado.get(c["arquivo"], []),
                                                       alvo if enquadrar else None)}
                elif any(a < float(c["inicio"]) + fonte and float(c["inicio"]) < b for a, b in usado.get(c["arquivo"], [])):
                    novo = max(b for _, b in usado[c["arquivo"]])  # reusado: continua de onde parou, sem repetir
                    if novo + fonte > _duracao(c["arquivo"]):
                        avisos.append(f"{os.path.basename(c['arquivo'])}: brutos insuficientes, trecho repetido")
                    else:
                        c = {**c, "inicio": novo}
                elif antes:  # trecho escolhido por quem planejou: a sobra da transição vem de antes dele
                    c = {**c, "inicio": max(0.0, float(c["inicio"]) - antes)}
                usado.setdefault(c["arquivo"], []).append((float(c.get("inicio", 0)), float(c.get("inicio", 0)) + fonte))
                enq = None
                if enquadrar:
                    r = _enquadre(c["arquivo"], float(c.get("inicio", 0)), fonte, w, h, *alvo)
                    enq = r and {"crop": r[0], "zoom": round(r[1], 2)}
                escolhas.append({"arquivo": os.path.basename(c["arquivo"]), "no_video": round(t0 + a0, 2),
                                 "inicio": c.get("inicio"), "duracao": round(a1 - a0, 2), "velocidade": vel,
                                 "enquadre": enq and enq["zoom"], "transicao": trans if k > 0 or bi > 0 else None})
                pulsos = []
                if golpes and pb.get("pulsos") and not c.get("continuo"):
                    fortes = sorted((f for _, f in golpes), reverse=True)
                    corte = fortes[max(0, len(bordas) - 1)] if len(fortes) >= len(bordas) else 0
                    pulsos = [g - t0 - a0 + antes for g, f in golpes if t0 + a0 + 0.25 < g < t0 + a1 - 0.15 and f >= corte]
                if k > 0 or bi > 0:
                    cortes_v.add(round(t0 + a0, 3))
                if trans in SOBREPOSICOES and _sons(pasta_visual, trans):
                    sobreposicoes.append((trans, t0 + a0))
                nome_sfx = c.get("sfx") or (p.get("sfx_nos_cortes") if k > 0 else None)
                if "sfx" not in c and not nome_sfx and pb.get("sfx_nas_transicoes"):
                    nome_sfx = SFX_DA_TRANSICAO.get(trans)  # o som acompanha a transição visual
                if nome_sfx:
                    if nome_sfx in SFX or _sons(pasta_sfx, nome_sfx):
                        sfx.append((nome_sfx, t0 + a0))
                    else:
                        avisos.append(f"efeito sonoro '{nome_sfx}' sem equivalente na rota local, ficou de fora")
                rot = f"b{bi}p{pi}c{k}"
                entrada = "corte" if trans in XFADE or trans in SOBREPOSICOES else trans
                filtros.append(_trecho(entra(c["arquivo"]), c, dur_total, pb, w, h, entrada, avisos, pulsos, vel, enq)
                               + f"[{rot}]")
                # partes do clipe: começo (entra na transição), corpo e fim (sai na transição seguinte)
                n_total = round(dur_total * FPS)
                cortes_k = [0] + ([sobre[k]] if sobre[k] else []) + ([n_total - sobre[k + 1]] if sobre[k + 1] else []) + [n_total]
                nomes_k = [f"{rot}s{j}" for j in range(len(cortes_k) - 1)]
                if len(nomes_k) == 1:
                    nomes_k = [rot]
                else:
                    filtros.append(f"[{rot}]split={len(nomes_k)}" + "".join(f"[{n}x]" for n in nomes_k))
                    for n, ini_q, fim_q in zip(nomes_k, cortes_k, cortes_k[1:]):
                        filtros.append(f"[{n}x]trim=start_frame={ini_q}:end_frame={fim_q},setpts=PTS-STARTPTS[{n}]")
                cabeca = nomes_k[0] if sobre[k] else None
                corpo = nomes_k[1 if sobre[k] else 0]
                if cabeca:  # transição: fim do clipe anterior com o começo deste
                    xf, nq = XFADE[trans]
                    a_, b_ = pedacos.pop(), cabeca
                    if xf == "custom":
                        meia = f"{w // 2 // 2 * 2}:{h // 2 // 2 * 2}"
                        filtros.append(f"[{a_}]scale={meia}[{rot}xa];[{b_}]scale={meia}[{rot}xb];[{rot}xa][{rot}xb]"
                                       f"xfade=transition=custom:duration={nq / FPS:.4f}:offset=0:expr='{XFADE_EASING}':threads=1,"
                                       f"scale={w}:{h},setsar=1[{rot}x]")
                    else:
                        filtros.append(f"[{a_}][{b_}]xfade=transition={xf}:duration={nq / FPS:.4f}:offset=0[{rot}x]")
                    pedacos.append(f"{rot}x")
                pedacos.append(corpo)
                if sobre[k + 1]:
                    pedacos.append(nomes_k[-1])
            filtros.append(f"{''.join(f'[{n}]' for n in pedacos)}concat=n={len(pedacos)}:v=1:a=0,"
                           f"tpad=stop_mode=clone:stop_duration={d:.3f},trim=duration={d:.3f}[b{bi}p{pi}]")
            filtros.append(f"[{ultimo}][b{bi}p{pi}]overlay={x}:{y}[b{bi}o{pi}]")
            ultimo = f"b{bi}o{pi}"
        filtros.append(f"[{ultimo}]trim=duration={d:.3f},setpts=PTS-STARTPTS,format=yuv420p[b{bi}]")
        nomes_blocos.append(f"[b{bi}]")
    filtros.append(f"{''.join(nomes_blocos)}concat=n={len(nomes_blocos)}:v=1:a=0[v]")
    if sobreposicoes:
        # camada só com as sobreposições (preto no resto) misturada em "tela": o preto não muda a imagem
        filtros.append(f"color=c=black:s={W}x{H}:r={FPS}:d={total:.3f},format=gbrp[ov0]")
        usados_v = {}
        for j, (nome, quando) in enumerate(sobreposicoes):
            arqs = _sons(pasta_visual, nome)
            arq = arqs[usados_v.get(nome, 0) % len(arqs)]
            usados_v[nome] = usados_v.get(nome, 0) + 1
            ini_ov = max(0.0, quando - _pico_visual(arq))
            filtros.append(f"[{entra(arq)}:v]scale={W}:{H},setsar=1,fps={FPS},format=gbrp,setpts=PTS-STARTPTS+{ini_ov:.3f}/TB[ovs{j}]")
            filtros.append(f"[ov{j}][ovs{j}]overlay=eof_action=pass:format=gbrp[ov{j + 1}]")
        op = float(p.get("sobreposicao_opacidade", 0.45))
        filtros.append(f"[v]format=gbrp[vr];[vr][ov{len(sobreposicoes)}]blend=all_mode=screen:all_opacity={op}:shortest=1,"
                       f"format=yuv420p[vfinal]")
    else:
        filtros.append("[v]null[vfinal]")

    mapa, audios = ["-map", "[vfinal]"], []
    if voz:
        iv = entra(absol(voz["arquivo"]), "-ss", f"{float(voz.get('inicio', 0)):.3f}")
        filtros.append(f"[{iv}:a]atrim=duration={total:.3f},asetpts=PTS-STARTPTS,"
                       f"aformat=sample_rates=44100:channel_layouts=stereo[voz]")
        audios.append("[voz]")
    if musica:
        im = entra(musica, "-ss", f"{m_ini:.3f}")
        vol = float(p.get("musica_volume", 0.25 if voz else 1.0))  # com voz, música fica de fundo
        filtros.append(f"[{im}:a]atrim=duration={total:.3f},asetpts=PTS-STARTPTS,volume={vol},"
                       f"afade=t=out:st={max(0, total - 0.5):.3f}:d=0.5,"
                       f"aformat=sample_rates=44100:channel_layouts=stereo[mus]")
        audios.append("[mus]")
    usados_sfx, niveis_sfx = {}, []
    abaixo = float(p.get("sfx_abaixo_db", 8))
    vol_musica = float(p.get("musica_volume", 0.25 if voz else 1.0))
    for k, (nome, quando) in enumerate(sfx):
        arquivos = _sons(pasta_sfx, nome)
        if arquivos:  # som do pacote, variando entre as versões; o pico cai no corte
            arq = arquivos[usados_sfx.get(nome, 0) % len(arquivos)]
            usados_sfx[nome] = usados_sfx.get(nome, 0) + 1
            idx = entra(arq)
            fonte, antes, nivel = f"[{idx}:a]anull", _pico(arq), _nivel_pico(arq)
        else:
            fonte, antes = SFX[nome]
            nivel = _nivel_pico(fonte)
        # o efeito nunca passa da música: o pico dele fica `sfx_abaixo_db` abaixo do nível da música naquele corte
        ref = _nivel_musica(musica, m_ini + quando, vol_musica) if musica else -20.0
        ganho = max(-40.0, min(12.0, ref - abaixo - nivel))
        niveis_sfx.append({"efeito": nome, "no_video": round(quando, 2), "musica_db": round(ref, 1),
                           "efeito_db": round(nivel + ganho, 1)})
        atraso = max(0, int((quando - antes) * 1000))
        filtros.append(f"{fonte},volume={ganho:.1f}dB,adelay={atraso}:all=1,"
                       f"aformat=sample_rates=44100:channel_layouts=stereo[sfx{k}]")
        audios.append(f"[sfx{k}]")
    if audios:
        filtros.append(f"{''.join(audios)}amix=inputs={len(audios)}:normalize=0:duration=longest[a]" if len(audios) > 1
                       else f"{audios[0]}anull[a]")
        mapa += ["-map", "[a]"]
    saida = absol(p.get("saida", "saida.mp4"))
    grafo = ";".join(filtros)
    if len(grafo) > 30000:  # perto do limite de linha de comando do Windows (32 767)
        raise SystemExit(f"plano grande demais para um render ({len(grafo)} caracteres de filtro); divida em menos clipes")
    _ffmpeg(["-y", *entradas, "-filter_complex", grafo, *mapa, "-t", f"{total:.3f}",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart", saida])
    sinc = None
    if golpes:  # cortes que caíram num golpe forte (±40 ms) e golpes fortes que ganharam corte
        piso = p.get("golpe_piso", 0.6)
        fortes = [g for g, f in golpes if 0.3 < g < total - 0.3 and f >= piso]
        perto = lambda x, ys: any(abs(x - y) <= 0.04 for y in ys)
        sinc = {"cortes": len(cortes_v), "cortes_no_golpe": sum(perto(c, fortes) for c in cortes_v),
                "golpes_fortes": len(fortes), "golpes_fortes_com_corte": sum(perto(g, cortes_v) for g in fortes)}
    for a in avisos:
        print("aviso:", a, file=sys.stderr)
    return {"saida": saida, "duracao": round(total, 3), "bpm": info and info["bpm"],
            "musica_inicio": round(m_ini, 3) if musica else None, "corte_no": corte_no, "sincronia": sinc,
            "cortes": sorted(cortes_v), "avisos": avisos, "clipes": escolhas, "efeitos_sonoros": niveis_sfx,
            "blocos": [{"layout": b.get("layout", "cheio"), "inicio": t0, "duracao": d} for b, t0, d in blocos]}


def _amostras_quadro(arquivo, t):
    """Cor média (RGB) do quadro em `t`."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", arquivo, "-frames:v", "1", "-vf", "scale=1:1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return raw[:3]


def teste():
    """Metrônomo sintético: o BPM e a fase medidos têm que bater com os gerados."""
    ok = True
    for bpm, fase in ((128.0, 0.37), (95.0, 0.12), (150.0, 0.05)):
        with tempfile.TemporaryDirectory() as d:
            arq = os.path.join(d, "click.wav")
            sr, dur = 22050, 12.0
            amost = array.array("h", [0]) * int(sr * dur)
            rnd = random.Random(1)
            for i in range(len(amost)):
                amost[i] = int(rnd.gauss(0, 300))
            t = fase
            while t < dur:
                i0 = int(t * sr)
                for j in range(int(0.03 * sr)):
                    if i0 + j < len(amost):
                        amost[i0 + j] += int(12000 * math.sin(2 * math.pi * 80 * j / sr) * math.exp(-j / (0.008 * sr)))
                t += 60 / bpm
            with wave.open(arq, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
                w.writeframes(amost.tobytes() if sys.byteorder == "little" else amost.byteswap() or amost.tobytes())
            r = batidas(arq, 0, dur)
            erro_fase = abs(((r["primeira"] - fase + 30 / bpm) % (60 / bpm)) - 30 / bpm)
            passou = abs(r["bpm"] - bpm) < 0.5 and erro_fase < 0.03
            ok &= passou
            print(f"{'ok ' if passou else 'ERRO'} bpm {bpm} -> {r['bpm']}, fase {fase} -> {r['primeira']} (erro {erro_fase*1000:.0f} ms)")
    # corte no grave, sem calibrar para uma música: seis gêneros sintéticos com gabarito (bumbo, caixa, chimbal),
    # baixo e ruído por cima. Exige: BPM certo (oitava aceita), todo corte num bumbo ou nota do baixo (nunca na
    # caixa ou no chimbal) e clipe médio de 0,45 a 2,5 s.
    generos = {  # bpm, bumbo e caixa em semicolcheias do compasso (0-15), chimbal a cada n semicolcheias
        "house": (124, [0, 4, 8, 12], [4, 12], 2),
        "funk": (130, [0, 3, 6, 10], [4, 12], 1),
        "trap": (140, [0, 7, 10], [8], 1),
        "reggaeton": (95, [0, 4, 8, 12], [3, 6, 11, 14], 2),
        "pop": (100, [0, 8, 10], [4, 12], 2),
        "balada": (72, [0], [8], 4),
    }
    for nome, (bpm, bumbo, caixa, chimbal) in generos.items():
        with tempfile.TemporaryDirectory() as d:
            arq = os.path.join(d, nome + ".wav")
            sr, dur = 22050, 16.0
            rnd = random.Random(nome)
            amost = [rnd.gauss(0, 900) + 900 * math.sin(2 * math.pi * 0.7 * k / sr) * rnd.gauss(0, 1) for k in range(int(sr * dur))]
            semi, gabarito = 60 / bpm / 4, []  # gabarito: só bumbo e baixo

            def bate(t, amp, freq, decai, ruido=False):
                i0 = int(t * sr)
                for j in range(int(decai * 6 * sr)):
                    if i0 + j < len(amost):
                        som = rnd.gauss(0, 1) if ruido else math.sin(2 * math.pi * freq * j / sr)
                        amost[i0 + j] += amp * som * math.exp(-j / (decai * sr))
            for compasso in range(int(dur / (16 * semi)) + 1):
                base = compasso * 16 * semi
                for q in range(16):
                    t = base + q * semi
                    if t >= dur:
                        break
                    if q in bumbo:
                        bate(t, 14000, 60, 0.03); gabarito.append(t)
                    if q in caixa:
                        bate(t, 9000, 0, 0.02, True)
                    if q % chimbal == 0:
                        bate(t, 1500, 0, 0.004, True)
                    if q in (0, 8):
                        bate(t, 3000, 110, 0.15); gabarito.append(t)  # baixo
            mx = max(abs(x) for x in amost) or 1
            pcm = array.array("h", [int(32000 * x / mx) for x in amost])
            with wave.open(arq, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
                w.writeframes(pcm.tobytes() if sys.byteorder == "little" else pcm.byteswap() or pcm.tobytes())
            r = batidas(arq, 0, dur)
            oitava = min(abs(r["bpm"] / bpm - f) for f in (0.5, 1, 2)) < 0.02
            cortes = _fronteiras(r["graves"], 0.0, 15.0, {"gancho_min": 1.0}, True)
            no_som = [c for c in cortes if any(abs(c - g) <= 0.04 for g in gabarito)]
            media = 15.0 / (len(cortes) + 1)
            passou = oitava and len(no_som) == len(cortes) and 0.45 <= media <= 2.5
            ok &= passou
            print(f"{'ok ' if passou else 'ERRO'} {nome:9s} bpm {bpm} -> {r['bpm']}; cortes no grave "
                  f"{len(no_som)}/{len(cortes)}; clipe médio {media:.2f} s")
    # início da música: efeito sonoro solto em 0,43 s e a batida em sequência só a partir de 3,62 s (caso do A01)
    marcas = [[0.43, 0.9]] + [[3.62 + k * 2 + d, 1.0] for k in range(6) for d in (0, 0.5)]
    cabe, curta = _inicio_musica(marcas, 0.6, 2.5, 5.0, 0.1), _inicio_musica(marcas, 0.6, 2.5, 1.2, 0.1)
    passou = cabe == (3.62, 3.62) and curta == (0.43, 3.62)
    ok &= passou
    print(f"{'ok ' if passou else 'ERRO'} início da música: pula a introdução quando cabe {cabe}, avisa quando não cabe {curta}")
    # transições entre clipes: com sobreposição (xfade), o vídeo tem que sair com o número exato de quadros
    with tempfile.TemporaryDirectory() as d:
        for n, cor in enumerate(("red", "blue", "green")):
            _ffmpeg(["-f", "lavfi", "-i", f"color=c={cor}:s=180x320:r=30:d=3", "-pix_fmt", "yuv420p",
                     os.path.join(d, f"c{n}.mp4")])
        plano = {"duracao": 3, "saida": "x.mp4", "clipes": [
            {"arquivo": "c0.mp4", "inicio": 0.5, "segundos": 1}, {"arquivo": "c1.mp4", "inicio": 0.5, "segundos": 1, "transicao": "combinar"},
            {"arquivo": "c2.mp4", "inicio": 0.5, "segundos": 1, "transicao": "desfoque_passagem"}]}
        with open(os.path.join(d, "p.json"), "w") as f:
            json.dump(plano, f)
        r = render(os.path.join(d, "p.json"))
        quadros = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                                      "stream=nb_read_frames", "-of", "csv=p=0", r["saida"]], capture_output=True, text=True).stdout)
        meio = list(_amostras_quadro(r["saida"], 1.0))  # no corte, metade de cada cor: vermelho e azul misturados
        passou = quadros == 90 and meio[0] > 60 and meio[2] > 60
        ok &= passou
        print(f"{'ok ' if passou else 'ERRO'} transições: {quadros} quadros de 90; no meio do combinar RGB {meio}")
    # rampa: a soma do tempo de saída tem que dar a duração do clipe
    for dur, vel in ((1.0, 0.5), (2.5, 0.4)):
        fonte, _ = _tempo(dur, vel, True)
        a = 0.3 * dur * (vel - 1) / math.log(vel)
        k = (vel - 1) / a
        saida = math.log(1 + k * a) / k + (fonte - a) / vel
        passou = abs(saida - dur) < 1e-6
        ok &= passou
        print(f"{'ok ' if passou else 'ERRO'} rampa {dur} s a {vel}: usa {fonte:.3f} s do bruto, sai {saida:.3f} s")
    # rastro: produto escuro sobre asfalto cinza, fora do centro, e uma mão (tom de pele) que não pode contar
    with tempfile.TemporaryDirectory() as d:
        arq = os.path.join(d, "produto.mp4")
        _ffmpeg(["-f", "lavfi", "-i", "color=c=0x808080:s=360x640:d=1:r=10", "-vf",
                 "drawbox=x=180:y=200:w=150:h=60:color=0x202030:t=fill,drawbox=x=0:y=380:w=200:h=120:color=0xE0A080:t=fill",
                 "-pix_fmt", "yuv420p", arq])
        _, _, q = _rastro(arq)
        cx, cy, larg, borda = q[0][1]
        passou = abs(cx - 255 / 360) < 0.04 and abs(cy - 230 / 640) < 0.03 and abs(larg - 150 / 360) < 0.1 and not borda
        ok &= passou
        print(f"{'ok ' if passou else 'ERRO'} rastro: centro ({cx:.2f}, {cy:.2f}) de (0.71, 0.36), largura {larg:.2f} de 0.42, mão ignorada")
    return ok


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "batidas" and len(sys.argv) > 2:
        print(json.dumps(batidas(sys.argv[2], *(float(x) for x in sys.argv[3:5])), ensure_ascii=False))
    elif cmd == "musica" and len(sys.argv) > 2:  # conferir a música antes de planejar
        m = conferir_musica(sys.argv[2], _receita({"receita": "corte-musical", "duracao": float(sys.argv[3]) if len(sys.argv) > 3 else 15}))
        print(json.dumps({k: v for k, v in m.items() if k not in ("info", "marcas", "analise")}, ensure_ascii=False))
    elif cmd == "render" and len(sys.argv) > 2:
        print(json.dumps(render(sys.argv[2]), ensure_ascii=False))
    elif cmd == "teste":
        sys.exit(0 if teste() else 1)
    else:
        print(__doc__)
        sys.exit(2)
