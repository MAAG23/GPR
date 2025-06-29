# Jogo de Voz

Um jogo interativo que utiliza reconhecimento de voz e detecção de pitch para controlar personagens em dois modos diferentes.

## Funcionalidades

### 1. **Desafio de Tonalidade**
- Controle uma bola usando a intensidade (pitch) da sua voz
- Navegue através de obstáculos ajustando o tom da sua voz
- Quanto mais agudo o som, mais alto a bola voa
- Estilo similar ao Flappy Bird

### 2. **Comandos de Voz**
- Controle um personagem usando comandos específicos de voz
- Comandos disponíveis:
  - **"correr"** - Faz o personagem correr
  - **"saltar"** ou **"pular"** - Faz o personagem pular
  - **"parar"** - Para o personagem
  - **"abaixar"** ou **"baixar"** - Faz o personagem abaixar

### 3. **Configuração de Microfone**
- Selecione seu microfone preferido
- Teste o microfone com visualizador de volume e pitch em tempo real
- Ajuste as configurações de áudio conforme necessário

## Instalação

### Pré-requisitos
- Python 3.7 ou superior
- Microfone funcionando

### Instalação das Dependências

1. **Clone ou baixe o projeto**
2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

### Dependências Específicas por Sistema

#### macOS
```bash
brew install portaudio
pip install pyaudio
```

#### Ubuntu/Debian
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

#### Windows
- O PyAudio geralmente instala automaticamente
- Se houver problemas, baixe o wheel apropriado de: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

## Como Usar

1. **Execute o jogo:**
   ```bash
   python voice_game.py
   ```

2. **Configurar Microfone:**
   - Clique em "Configurar Microfone"
   - Selecione seu microfone na lista
   - Clique em "Testar Microfone" para verificar se está funcionando
   - Fale ou faça sons para ver as barras de volume e pitch

3. **Jogar:**
   - **Desafio de Tonalidade:** Use sua voz para controlar a altura da bola
   - **Comandos de Voz:** Fale os comandos claramente para controlar o personagem

## Controles

### Desafio de Tonalidade
- **Voz aguda:** Bola sobe
- **Voz grave:** Bola desce
- **Silêncio:** Bola vai para o chão

### Comandos de Voz
- **"correr":** Personagem corre (cor verde)
- **"saltar/pular":** Personagem pula (cor amarela)
- **"parar":** Personagem para (cor azul)
- **"abaixar/baixar":** Personagem abaixa (cor laranja)

## Dicas

1. **Configuração do Microfone:**
   - Teste diferentes microfones se houver problemas
   - Certifique-se de que o microfone está sendo detectado pelo sistema
   - Ajuste o volume do microfone nas configurações do sistema

2. **Jogabilidade:**
   - Fale claramente para melhor reconhecimento
   - Mantenha distância adequada do microfone
   - Evite ruídos de fundo quando possível

3. **Desempenho:**
   - Feche outros aplicativos que usam microfone
   - Certifique-se de ter conexão com internet (para reconhecimento de voz)

## Solução de Problemas

### Erro de Microfone
- Verifique se o microfone está conectado
- Teste o microfone em outras aplicações
- Reselecione o microfone nas configurações do jogo

### Reconhecimento de Voz Não Funciona
- Verifique sua conexão com a internet
- Fale mais claramente e alto
- Reduza ruídos de fundo

### Erro de Dependências
- Certifique-se de ter instalado todas as dependências
- Tente reinstalar com: `pip install -r requirements.txt --force-reinstall`

## Requisitos do Sistema

- **Sistema Operacional:** Windows, macOS, Linux
- **Python:** 3.7+
- **Memória:** 512MB RAM mínimo
- **Audio:** Microfone funcional
- **Rede:** Conexão com internet (para reconhecimento de comandos)

## Créditos

Jogo desenvolvido com:
- **Pygame** - Interface gráfica e game engine
- **Aubio** - Detecção de pitch
- **SpeechRecognition** - Reconhecimento de comandos de voz
- **SoundDevice** - Captura de áudio
- **NumPy** - Processamento de dados de áudio 