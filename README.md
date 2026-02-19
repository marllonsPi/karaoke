# Karaoke com nota (Raspberry Pi 3)

Objetivo: um karaoke que toca a musica, mostra a letra e gera nota por afinacao e ritmo, rodando em Raspberry Pi 3.

## Requisitos recomendados (Pi 3)
- Raspberry Pi OS **32-bit** (melhor compatibilidade e menor consumo de RAM no Pi 3).
- Microfone USB e saida HDMI para TV.
- Audio em WAV (PCM) para reduzir uso de CPU.

## Estrutura de uma musica
Cada musica fica em uma pasta dentro de `songs/`:

```
songs/
  minha-musica/
    audio.wav
    lyrics.lrc
    melody.csv
    meta.json  (opcional)
```

### `lyrics.lrc`
Formato LRC simples:
```
[00:05.00]Primeira linha
[00:10.50]Segunda linha
```

### `melody.csv`
Arquivo CSV com a melodia de referencia (uma nota por linha):
```
start_s,duration_s,midi
0.50,0.40,64
0.90,0.60,62
```
- `start_s`: tempo em segundos desde o inicio da musica
- `duration_s`: duracao da nota em segundos
- `midi`: numero MIDI (60 = C4)

> Se voce tiver MIDI, podemos adicionar um conversor para `melody.csv`.

## Importar UltraStar (recomendado)
Para usar bibliotecas existentes de karaoke, importe um arquivo UltraStar (.txt) assim:
```
python3 tools/import_ultrastar.py --source /caminho/para/ultrastar/musica --dest songs/minha-musica
```

Se a musica ficar fora do tempo, ajuste:
```
python3 tools/import_ultrastar.py --source /caminho/para/ultrastar/musica --dest songs/minha-musica --ticks-per-beat 4
```

Se o arquivo tiver `#RELATIVE:YES`, rode com:
```
python3 tools/import_ultrastar.py --source /caminho/para/ultrastar/musica --dest songs/minha-musica --relative
```

## Buscar musicas online (Performous)
Para baixar pacotes oficiais e importar automaticamente:
```
python3 tools/fetch_performous.py --list
python3 tools/fetch_performous.py --package libre --dest songs
```

Para baixar todos os pacotes encontrados:
```
python3 tools/fetch_performous.py --all --dest songs
```

As musicas serao importadas em `songs/<pacote>/...`.

## Rodar
```
./run.sh --song songs/minha-musica --fullscreen
```

## Dependencias
Instale via pip:
```
pip3 install -r requirements.txt
```

No Raspberry Pi, pode ser necessario instalar bibliotecas de audio do sistema:
```
sudo apt-get install -y libportaudio2 portaudio19-dev
```

Se o sistema estiver com PEP 668 ativo, use venv:
```
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

## Observacoes importantes
- Use fone ou volume baixo para evitar o audio da musica entrar no microfone.
- A pontuacao de ritmo compara o inicio das notas cantadas com a melodia de referencia.
- A pontuacao de afinacao compara o pitch cantado com a nota de referencia (em cents).
- O Raspberry Pi 3 nao tem entrada de microfone. Para microfones P10, use uma interface de audio USB com pre-amp.
# karaoke
