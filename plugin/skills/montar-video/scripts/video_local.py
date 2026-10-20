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


def _cortes(clipes, p, grade, total, t0=0.0, golpes=None):
    """Tempos (início, fim) de cada clipe no painel.

    Com `golpes` (picos da música em tempo de vídeo) e `cortar_nos_golpes`, cada corte cai no próximo golpe
    forte: o gancho vai até o primeiro golpe forte depois de `gancho_min` s; depois, nenhum clipe fica com
    menos de `corte_min` s, e se não vier golpe forte em `corte_max` s o corte vai no golpe mais forte do
    fim da janela. Sem golpes, usa a grade de batidas (`batidas_por_corte`) ou segundos."""
    padrao = p.get("batidas_por_corte", 2)
    padrao = padrao if isinstance(padrao, list) else [padrao]
    forte, cmin, cmax = p.get("golpe_forte", 0.65), p.get("corte_min", 0.45), p.get("corte_max", 2.5)
    partes, t, i = [], 0.0, 0
    while t < total - 1e-3 and clipes:
        c = clipes[i % len(clipes)]
        if c.get("continuo") or len(clipes) == 1:  # segue o painel inteiro (quem fala, ou painel de um clipe só)
            n_seg = total - t
        elif golpes and p.get("cortar_nos_golpes") and not c.get("batidas"):
            agora = t0 + t
            lo, hi = (p.get("gancho_min", 1.5), p.get("gancho_max", 4.0)) if i == 0 else (cmin, cmax)
            cand = [g for g in golpes if agora + lo - 1e-3 <= g[0] <= agora + hi + 1e-3]
            fortes = [g for g in cand if g[1] >= forte]
            if fortes:
                alvo = fortes[0][0]
            elif [g for g in cand if g[0] >= agora + 0.6 * hi]:  # sem golpe forte: estica o clipe
                alvo = max((g for g in cand if g[0] >= agora + 0.6 * hi), key=lambda g: g[1])[0]
            else:
                alvo = agora + (2 * grade if grade else hi)
            n_seg = alvo - agora
        elif grade:
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


# Repertório da Vitória (D01) em filtros do ffmpeg. Transição = início do clipe que entra, no golpe.
TRANSICOES = {
    "corte": "",
    "flash": "fade=t=in:st=0:d=0.12:color=white",
    "fade": "fade=t=in:st=0:d=0.2",
    "desfoque": "boxblur=20:2:enable='lt(t,0.13)'",
    "brilho": "eq=brightness=0.28:contrast=1.15:enable='lt(t,0.1)',fade=t=in:st=0:d=0.1:color=white",
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
    "swoosh": ("anoisesrc=d=0.4:c=pink:a=0.6:r=44100,highpass=f=700,lowpass=f=5000,afade=t=in:d=0.28,afade=t=out:st=0.28:d=0.12", 0.28),
    "pop": ("sine=f=520:d=0.07:sample_rate=44100,afade=t=out:st=0.01:d=0.06", 0.0),
    "click": ("sine=f=2600:d=0.02:sample_rate=44100,afade=t=out:d=0.02", 0.0),
    "glitch": ("anoisesrc=d=0.15:a=0.5:r=44100,acrusher=bits=3:samples=30:mix=1", 0.0),
    "vento": ("anoisesrc=d=0.8:c=brown:a=0.5:r=44100,lowpass=f=500,afade=t=in:d=0.4,afade=t=out:st=0.4:d=0.4", 0.4),
}
SFX.update({"woosh": SFX["swoosh"], "swish": SFX["swoosh"], "shun": SFX["swoosh"]})
SEM_EQUIVALENTE = {"combinar", "radial_blur", "typing", "typewriting"}


def _trecho(idx, c, dur, p, w, h, transicao, avisos):
    """Filtro de um clipe: recorte do bruto, enquadramento sem barras, zoom, transição de entrada e efeito."""
    origem = float(c.get("inicio", 0))
    disp = _duracao(c["arquivo"])
    origem = max(0.0, min(origem, disp - dur)) if disp > dur else 0.0
    f = (f"[{idx}:v]trim=start={origem:.3f}:duration={dur:.3f},setpts=PTS-STARTPTS,fps={FPS},"
         f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1")
    if disp < origem + dur:  # bruto curto: segura o último quadro em vez de cortar o tempo
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
            pulo = 0
            if auto:  # começa no primeiro golpe forte que ainda deixa música para o vídeo inteiro
                sobra = _duracao(musica) - float(p.get("duracao", 15)) - info["primeira"]
                pulo = next((k for k, f in enumerate(info["forca_meias"]) if f >= 0.5 and k * grade / 2 <= sobra), 0)
                info["forca_meias"] = info["forca_meias"][pulo:]
            if _duracao(musica) - (m_ini + info["primeira"] + pulo * grade / 2) < float(p.get("duracao", 15)) - 0.05:
                print("aviso: a música acaba antes do vídeo; o final fica sem som", file=sys.stderr)
            m_ini += info["primeira"] + pulo * grade / 2  # o vídeo começa numa batida
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
    avisos, sfx, cortes_v = [], [], []
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
            for k, (c, a0, a1) in enumerate(_cortes(clipes, {**p, **b}, grade, d, t0, golpes)):
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
                if (k > 0 or bi > 0) and pi == 0:
                    cortes_v.append(round(t0 + a0, 3))
                nome_sfx = c.get("sfx") or (p.get("sfx_nos_cortes") if k > 0 else None)
                if nome_sfx:
                    if nome_sfx in SFX:
                        sfx.append((nome_sfx, t0 + a0))
                    else:
                        avisos.append(f"efeito sonoro '{nome_sfx}' sem equivalente na rota local, ficou de fora")
                rot = f"b{bi}p{pi}c{k}"
                filtros.append(_trecho(entra(c["arquivo"]), c, a1 - a0, {**p, **b}, w, h, trans, avisos) + f"[{rot}]")
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
        filtros.append(f"{fonte},volume={float(p.get('sfx_volume', 0.5))},adelay={atraso}:all=1,"
                       f"aformat=sample_rates=44100:channel_layouts=stereo[sfx{k}]")
        audios.append(f"[sfx{k}]")
    if audios:
        filtros.append(f"{''.join(audios)}amix=inputs={len(audios)}:normalize=0:duration=first[a]" if len(audios) > 1
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
        fortes = [g for g, f in golpes if f >= p.get("golpe_forte", 0.65) and 0.3 < g < total - 0.3]
        perto = lambda x, ys: any(abs(x - y) <= 0.05 for y in ys)
        sinc = {"cortes": len(cortes_v), "cortes_no_golpe": sum(perto(c, [g for g, _ in golpes]) for c in cortes_v),
                "golpes_fortes": len(fortes), "golpes_fortes_com_corte": sum(perto(g, cortes_v) for g in fortes)}
    for a in avisos:
        print("aviso:", a, file=sys.stderr)
    return {"saida": saida, "duracao": round(total, 3), "bpm": info and info["bpm"],
            "musica_inicio": round(m_ini, 3) if musica else None, "sincronia": sinc,
            "cortes": cortes_v, "avisos": avisos,
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
    # corte nos golpes: 120 BPM com golpes fortes irregulares (padrão do exemplo A01) e batidas fracas
    with tempfile.TemporaryDirectory() as d:
        arq = os.path.join(d, "golpes.wav")
        sr, dur = 22050, 14.0
        rnd = random.Random(2)
        amost = array.array("h", [int(rnd.gauss(0, 200)) for _ in range(int(sr * dur))])
        fortes = [1.0, 2.5, 3.0, 5.0, 6.5, 7.0, 9.0, 10.5, 11.0]
        for k in range(int(dur / 0.5)):
            t = k * 0.5
            amp = 14000 if t in fortes else 2500
            i0 = int(t * sr)
            for j in range(int(0.04 * sr)):
                if i0 + j < len(amost):
                    amost[i0 + j] = max(-32000, min(32000, amost[i0 + j] + int(amp * math.sin(2 * math.pi * 70 * j / sr) * math.exp(-j / (0.01 * sr)))))
        with wave.open(arq, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes(amost.tobytes() if sys.byteorder == "little" else amost.byteswap() or amost.tobytes())
        r = batidas(arq, 0, dur)
        clipes = [{"arquivo": "x"}] * 20
        cortes = [t1 for _, _, t1 in _cortes(clipes, {"cortar_nos_golpes": True, "gancho_min": 0.5}, 60 / r["bpm"],
                                              12.0, 0.0, r["golpes"])][:-1]
        perdidos = [f for f in fortes[1:] if f < 12 and not any(abs(f - c) <= 0.05 for c in cortes)]
        fora = [c for c in cortes if not any(abs(f - c) <= 0.05 for f in fortes)]
        passou = not perdidos and not fora
        ok &= passou
        print(f"{'ok ' if passou else 'ERRO'} cortes nos golpes: {cortes}; perdidos {perdidos}; fora {fora}")
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
