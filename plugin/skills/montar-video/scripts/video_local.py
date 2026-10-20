"""Rota local do montar-video: batida da música e render do MP4 com ffmpeg.

Só biblioteca padrão do Python; precisa do ffmpeg no PATH.

    py -B -I video_local.py batidas musica.m4a        (Windows; python3 no macOS/Linux)
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


def _amostras(caminho, inicio=0.0, dur=60.0):
    out = _ffmpeg(["-ss", str(inicio), "-t", str(dur), "-i", caminho, "-vn", "-ac", "1", "-ar", str(SR),
                   "-f", "s16le", "-"], capture_output=True).stdout
    a = array.array("h")
    a.frombytes(out[: len(out) // 2 * 2])
    if sys.byteorder == "big":
        a.byteswap()
    return a


def _envelope(a):
    """Fluxo de energia (log) por quadro, só subidas: marca onde a música 'bate'."""
    env, prev = [], None
    for i in range(0, len(a) - HOP, HOP):
        e = math.log1p(sum(x * x for x in a[i:i + HOP]) / HOP)
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


def batidas(caminho, inicio=0.0, dur=60.0, bpm_min=70, bpm_max=180):
    """Devolve {bpm, primeira, batidas[]} em segundos a partir de `inicio`.

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
    # golpes: picos do envelope (máximo local em ±80 ms), com força 0..1; é onde quem edita corta
    w = int(0.08 * qps)
    picos = [i for i in range(len(env)) if env[i] > 0 and env[i] == max(env[max(0, i - w):i + w + 1])]
    alt = sorted(env[i] for i in picos) or [1.0]
    teto = alt[int(0.95 * (len(alt) - 1))] or 1.0  # percentil 95: um pico isolado não achata os outros
    golpes = [[round(i / qps, 4), round(min(1.0, env[i] / teto), 3)] for i in picos if env[i] >= 0.15 * teto]
    return {"bpm": round(bpm, 2), "primeira": round(primeira, 4), "batidas": lista,
            "forca_meias": [round(f / topo, 3) for f in forcas], "golpes": golpes}


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


def _fronteiras(golpes, ini, dur, p, grade, abertura):
    """Onde cortar dentro de [ini, ini+dur], sem limiar fixo: vale para qualquer música.

    A densidade vem do andamento (`batidas_media` batidas por clipe, entre `corte_min` e 1,6 s) e é teto,
    não cota: os cortes são os golpes mais fortes daquela música (acima de `golpe_piso` da força dos golpes
    fortes dela) que respeitam o espaçamento mínimo; música esparsa fica com clipes mais longos. Trecho longo sem golpe
    escolhido recebe o golpe mais forte do meio dele. Na abertura, o gancho termina no golpe mais forte
    entre `gancho_min` e `gancho_max`."""
    cmin, cmax = p.get("corte_min", 0.45), p.get("corte_max", 2.5)
    batida = grade or 0.5
    medio = max(cmin, min(1.6, p.get("batidas_media", 1.5) * batida))
    fim = ini + dur
    piso = p.get("golpe_piso", 0.3)  # relativo aos golpes fortes desta música (escala já normalizada por faixa)
    golpes = [g for g in golpes if g[1] >= piso]
    dentro = [g for g in golpes if ini + cmin <= g[0] <= fim - cmin]
    aceitos = []
    if abertura:
        gancho = [g for g in dentro if ini + p.get("gancho_min", 1.5) <= g[0] <= ini + p.get("gancho_max", 4.0)]
        if gancho:
            aceitos.append(max(gancho, key=lambda g: (g[1], -g[0])))
    alvo = max(1, round(dur / medio) - 1)
    for g in sorted(dentro, key=lambda g: -g[1]):
        if len(aceitos) >= alvo:
            break
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
            meio = [g for g in golpes if a + cmin <= g[0] <= b - cmin] if b - a > limite else []
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
        bordas = [0.0] + [_quadro(t - t0) for t in _fronteiras(golpes, t0, total, p, grade, abertura)] + [_quadro(total)]
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


def _melhor_trecho(arquivo, dur, ocupados=()):
    """Início da janela mais viva e nítida do bruto, fora do começo e do fim (mão entrando, tremido)
    e sem repetir trechos já usados. Movimento acima do percentil 90 conta como 90 (chacoalhão não vale mais)."""
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
    s = margem
    while s + dur <= total - margem + 1e-6:
        if all(s + dur <= a or s >= b for a, b in ocupados):
            jan = [x for x in q if s <= x[0] < s + dur] or q[:1]
            nota = sum(min(x[1], teto) for x in jan) / len(jan) / teto - 0.5 * sum(x[2] for x in jan) / len(jan) / mediana_b
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
    # ganhos medidos para que todos tenham pico perto de -6 dBFS antes de `sfx_volume`
    "swoosh": ("anoisesrc=d=0.4:c=pink:a=0.6:r=44100,highpass=f=700,lowpass=f=5000,afade=t=in:d=0.28,afade=t=out:st=0.28:d=0.12,volume=9dB", 0.28),
    "pop": ("sine=f=520:d=0.07:sample_rate=44100,afade=t=out:st=0.01:d=0.06,volume=12dB", 0.0),
    "click": ("sine=f=2600:d=0.02:sample_rate=44100,afade=t=out:d=0.02,volume=12dB", 0.0),
    "glitch": ("anoisesrc=d=0.15:a=0.5:r=44100,acrusher=bits=3:samples=30:mix=1", 0.0),
    "vento": ("anoisesrc=d=0.8:c=brown:a=0.5:r=44100,lowpass=f=500,afade=t=in:d=0.4,afade=t=out:st=0.4:d=0.4,volume=6dB", 0.4),
}
SFX.update({"woosh": SFX["swoosh"], "swish": SFX["swoosh"], "shun": SFX["swoosh"]})
SFX_DA_TRANSICAO = {"zoom_in": "swoosh", "zoom_out": "swoosh", "desfoque": "swoosh", "flash_falha": "glitch"}
SEM_EQUIVALENTE = {"combinar", "radial_blur", "typing", "typewriting"}


def _trecho(idx, c, dur, p, w, h, transicao, avisos, pulsos=(), velocidade=1.0):
    """Filtro de um clipe: recorte do bruto, enquadramento sem barras, velocidade, zoom com pulsos nos
    golpes de dentro do clipe, transição de entrada e efeito."""
    fonte = dur * velocidade  # câmera lenta usa menos tempo do bruto
    origem = float(c.get("inicio", 0))
    disp = _duracao(c["arquivo"])
    origem = max(0.0, min(origem, disp - fonte)) if disp > fonte else 0.0
    lento = f",setpts=PTS/{velocidade}" if velocidade != 1.0 else ""
    f = (f"[{idx}:v]trim=start={origem:.3f}:duration={fonte:.3f},setpts=PTS-STARTPTS{lento},fps={FPS},"
         f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1")
    if disp < origem + fonte:  # bruto curto: segura o último quadro em vez de cortar o tempo
        f += f",tpad=stop_mode=clone:stop_duration={dur:.3f},trim=duration={dur:.3f}"
    for nome in [transicao] + list(c.get("efeitos") or ([c["efeito"]] if c.get("efeito") else [])):
        if nome in SEM_EQUIVALENTE or (nome not in TRANSICOES and nome not in EFEITOS):
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
    return f + ",setsar=1"


def render(plano_path):
    with open(plano_path, encoding="utf-8") as f:
        p = _receita(json.load(f))
    base = os.path.dirname(os.path.abspath(plano_path))
    absol = lambda x: x if os.path.isabs(x) else os.path.join(base, x)
    musica, voz = p.get("musica"), p.get("voz")
    auto = p.get("musica_inicio") in (None, "auto")
    m_ini, grade, info, golpes = 0.0 if auto else float(p["musica_inicio"]), None, None, None
    analise = m_ini
    if musica:
        musica = absol(musica)
        if p.get("no_ritmo", True):
            info = batidas(musica, m_ini, 90)
            grade = 60 / info["bpm"]
            inicio_rel = info["primeira"]  # sem auto: o vídeo começa na primeira batida
            if auto:  # começa no primeiro golpe forte que ainda deixa música para o vídeo inteiro
                sobra = _duracao(musica) - float(p.get("duracao", 15))
                forcas = sorted(f for _, f in info["golpes"])
                p75 = forcas[int(0.75 * (len(forcas) - 1))] if forcas else 1.0
                inicio_rel = next((g for g, f in info["golpes"] if f >= p75 and g <= sobra), info["primeira"])
            if _duracao(musica) - (m_ini + inicio_rel) < float(p.get("duracao", 15)) - 0.05:
                print("aviso: a música acaba antes do vídeo; o final fica sem som", file=sys.stderr)
            m_ini += inicio_rel
            golpes = [[round(g - (m_ini - analise), 4), f] for g, f in info["golpes"] if g - (m_ini - analise) > -0.02]

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
    avisos, sfx, cortes_v, usado, escolhas = [], [], set(), {}, []  # usado: trechos já usados de cada bruto
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
            for k, (c, a0, a1) in enumerate(partes):
                vel = 1.0
                if pb.get("lento") and not c.get("continuo") and a1 - a0 >= pb.get("lento_min", 1.2):
                    vel = float(pb["lento"])  # clipe longo respira em câmera lenta leve
                vel = float(c.get("velocidade", vel))
                fonte = (a1 - a0) * vel
                if c.get("continuo"):
                    pass
                elif c.get("inicio") in (None, "auto"):  # escolhe a janela mais viva e nítida ainda não usada
                    c = {**c, "inicio": _melhor_trecho(c["arquivo"], fonte, usado.get(c["arquivo"], []))}
                elif any(a < float(c["inicio"]) + fonte and float(c["inicio"]) < b for a, b in usado.get(c["arquivo"], [])):
                    novo = max(b for _, b in usado[c["arquivo"]])  # reusado: continua de onde parou, sem repetir
                    if novo + fonte > _duracao(c["arquivo"]):
                        avisos.append(f"{os.path.basename(c['arquivo'])}: brutos insuficientes, trecho repetido")
                    else:
                        c = {**c, "inicio": novo}
                usado.setdefault(c["arquivo"], []).append((float(c.get("inicio", 0)), float(c.get("inicio", 0)) + fonte))
                escolhas.append({"arquivo": os.path.basename(c["arquivo"]), "no_video": round(t0 + a0, 2),
                                 "inicio": c.get("inicio"), "duracao": round(a1 - a0, 2), "velocidade": vel})
                pulsos = []
                if golpes and pb.get("pulsos") and not c.get("continuo"):
                    fortes = sorted((f for _, f in golpes), reverse=True)
                    corte = fortes[max(0, len(bordas) - 1)] if len(fortes) >= len(bordas) else 0
                    pulsos = [g - t0 - a0 for g, f in golpes if t0 + a0 + 0.25 < g < t0 + a1 - 0.15 and f >= corte]
                flash = flash_modo == "todos" or (flash_modo == "gancho" and bi == 0 and pi == 0 and k == 1) \
                    or (flash_modo == "blocos" and k == 0 and bi > 0)
                if "transicao" in c:
                    trans = c["transicao"]
                elif k == 0 and not (bi > 0 and flash):
                    trans = "corte"
                elif flash:
                    trans = "flash"
                else:
                    trans = giro[(k - 1) % len(giro)] if giro else "corte"
                if k > 0 or bi > 0:
                    cortes_v.add(round(t0 + a0, 3))
                nome_sfx = c.get("sfx") or (p.get("sfx_nos_cortes") if k > 0 else None)
                if "sfx" not in c and not nome_sfx and pb.get("sfx_nas_transicoes"):
                    nome_sfx = SFX_DA_TRANSICAO.get(trans)  # o som acompanha a transição visual
                if nome_sfx:
                    if nome_sfx in SFX:
                        sfx.append((nome_sfx, t0 + a0))
                    else:
                        avisos.append(f"efeito sonoro '{nome_sfx}' sem equivalente na rota local, ficou de fora")
                rot = f"b{bi}p{pi}c{k}"
                filtros.append(_trecho(entra(c["arquivo"]), c, a1 - a0, pb, w, h, trans, avisos, pulsos, vel) + f"[{rot}]")
                nomes.append(f"[{rot}]")
            filtros.append(f"{''.join(nomes)}concat=n={len(nomes)}:v=1:a=0,"
                           f"tpad=stop_mode=clone:stop_duration={d:.3f},trim=duration={d:.3f}[b{bi}p{pi}]")
            filtros.append(f"[{ultimo}][b{bi}p{pi}]overlay={x}:{y}[b{bi}o{pi}]")
            ultimo = f"b{bi}o{pi}"
        filtros.append(f"[{ultimo}]trim=duration={d:.3f},setpts=PTS-STARTPTS,format=yuv420p[b{bi}]")
        nomes_blocos.append(f"[b{bi}]")
    filtros.append(f"{''.join(nomes_blocos)}concat=n={len(nomes_blocos)}:v=1:a=0[v]")

    mapa, audios = ["-map", "[v]"], []
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
    for k, (nome, quando) in enumerate(sfx):
        fonte, antes = SFX[nome]
        atraso = max(0, int((quando - antes) * 1000))
        filtros.append(f"{fonte},volume={float(p.get('sfx_volume', 0.35))},adelay={atraso}:all=1,"
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
    if golpes:  # quantos golpes fortes ganharam corte e quantos cortes caíram em golpe (±50 ms)
        dentro = [(g, f) for g, f in golpes if 0.3 < g < total - 0.3]
        corte_f = sorted((f for _, f in dentro), reverse=True)[max(0, len(cortes_v) - 1)] if dentro else 1
        fortes = [g for g, f in dentro if f >= corte_f]  # os N golpes mais fortes, N = número de cortes
        perto = lambda x, ys: any(abs(x - y) <= 0.05 for y in ys)
        sinc = {"cortes": len(cortes_v), "cortes_no_golpe": sum(perto(c, [g for g, _ in golpes]) for c in cortes_v),
                "golpes_fortes": len(fortes), "golpes_fortes_com_corte": sum(perto(g, cortes_v) for g in fortes)}
    for a in avisos:
        print("aviso:", a, file=sys.stderr)
    return {"saida": saida, "duracao": round(total, 3), "bpm": info and info["bpm"],
            "musica_inicio": round(m_ini, 3) if musica else None, "sincronia": sinc,
            "cortes": sorted(cortes_v), "avisos": avisos, "clipes": escolhas,
            "blocos": [{"layout": b.get("layout", "cheio"), "inicio": t0, "duracao": d} for b, t0, d in blocos]}


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
    # corte nos golpes, sem calibrar para uma música: seis gêneros sintéticos com gabarito (bumbo, caixa, chimbal),
    # baixo e ruído por cima. Exige: BPM certo (oitava aceita), cortes em som real e clipe médio de 0,45 a 2,5 s.
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
            semi, gabarito = 60 / bpm / 4, []

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
                        bate(t, 9000, 0, 0.02, True); gabarito.append(t)
                    if q % chimbal == 0:
                        bate(t, 1500, 0, 0.004, True); gabarito.append(t)
                    if q in (0, 8):
                        bate(t, 3000, 110, 0.15)  # baixo
            mx = max(abs(x) for x in amost) or 1
            pcm = array.array("h", [int(32000 * x / mx) for x in amost])
            with wave.open(arq, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
                w.writeframes(pcm.tobytes() if sys.byteorder == "little" else pcm.byteswap() or pcm.tobytes())
            r = batidas(arq, 0, dur)
            oitava = min(abs(r["bpm"] / bpm - f) for f in (0.5, 1, 2)) < 0.02
            cortes = _fronteiras(r["golpes"], 0.0, 15.0, {"gancho_min": 1.0}, 60 / r["bpm"], True)
            no_som = [c for c in cortes if any(abs(c - g) <= 0.04 for g in gabarito)]
            media = 15.0 / (len(cortes) + 1)
            passou = oitava and len(no_som) == len(cortes) and 0.45 <= media <= 2.5
            ok &= passou
            print(f"{'ok ' if passou else 'ERRO'} {nome:9s} bpm {bpm} -> {r['bpm']}; cortes em som real "
                  f"{len(no_som)}/{len(cortes)}; clipe médio {media:.2f} s")
    return ok


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "batidas" and len(sys.argv) > 2:
        print(json.dumps(batidas(sys.argv[2], *(float(x) for x in sys.argv[3:5])), ensure_ascii=False))
    elif cmd == "render" and len(sys.argv) > 2:
        print(json.dumps(render(sys.argv[2]), ensure_ascii=False))
    elif cmd == "teste":
        sys.exit(0 if teste() else 1)
    else:
        print(__doc__)
        sys.exit(2)
