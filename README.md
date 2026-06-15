# UNABOARD

UNABOARD é um painel local de monitoramento de sistema feito em Python, Streamlit, HTML, CSS e JavaScript.

O projeto exibe informações de hardware, rede, processos, histórico de uso e também possui um chatbot integrado à API local, pensado para ajudar a interpretar os dados do computador.

---

## Visão geral

O painel mostra dados como:

- Uso de CPU
- Uso de memória RAM
- Uso de GPU
- Memória de vídeo, dedicada e compartilhada
- Uso de disco
- Download e upload
- Ping, packet loss e jitter
- Processos em execução
- Gráficos com histórico
- Chatbot com análise dos dados do sistema

O Streamlit é responsável por renderizar o dashboard, mas a coleta principal dos dados fica centralizada no `main.py`.

---

## Estrutura do projeto

```text
MoniSNMP/
├──assets/
│   ├── css/
│   │   ├── dashboard.css
│   │   ├── responsive.css
│   │   └── streamlit_host.css
│   ├── icons/
│   │   └── arquivos .svg
│   ├── js/
│   │   ├── core.js
│   │   ├── animacao.js
│   │   ├── responsivo.js
│   │   ├── monitor.js
│   │   ├── chatbot.js
│   └── └── app.js
├── dados/
│   ├── cpu.py
│   ├── memoria.py
│   ├── gpu.py
│   ├── rede.py
│   ├── rede_qualidade.py
│   ├── disco.py
│   └── processos.py
├── historico/
│   ├── historico.json
│   └── ultimo_refresh.txt
├── chatbot.py
├── chatbot_api.py
├── diagnostico_gpu_taskmanager.py
├── index.html
├── main.py
├── README.md
├── requirements.txt
└── streamlit_app.py


```

---

## Função dos principais arquivos

### `streamlit_app.py`

Arquivo principal da interface.

Ele:

- carrega o layout HTML;
- carrega os arquivos CSS;
- carrega os arquivos JavaScript;
- chama o `main.py` para registrar um snapshot;
- renderiza os cards do dashboard;
- exibe os gráficos com base no histórico.

O Streamlit usa o `main.py` através da função:

```python
main.registrar_uma_vez()
```

---

### `main.py`

Arquivo central de coleta.

Ele coleta os dados do sistema e salva no histórico:

```text
historico/historico.json
```

Também gera um arquivo de diagnóstico:

```text
historico/ultimo_refresh.txt
```

Esse arquivo ajuda a confirmar se o Streamlit realmente chamou o `main.py`.

---

### `chatbot.py`

Contém a lógica do assistente do UNABOARD.

Ele coleta os dados atuais do sistema, monta um relatório e envia para o modelo Gemini responder em português brasileiro.

A chave da Gemini pode ser configurada diretamente no arquivo ou por variável de ambiente.

---

### `chatbot_api.py`

Cria uma API local com FastAPI.

Essa API recebe as mensagens do card de chat e consulta o `chatbot.py`.

Endpoint principal:

```text
POST http://127.0.0.1:8765/chat
```

Endpoints úteis:

```text
GET http://127.0.0.1:8765/health
GET http://127.0.0.1:8765/docs
```

---

## Diagnóstico de GPU

O arquivo `diagnostico_gpu_taskmanager.py` é um script auxiliar usado para investigar como o Windows está expondo as informações da GPU para o sistema.

Ele não faz parte diretamente da interface principal do dashboard, mas serve como ferramenta de diagnóstico para validar se os dados de GPU estão sendo retornados corretamente antes de serem usados no painel.

O script executa comandos PowerShell através do Python e organiza a saída em seções separadas:

### GPU BASIC INFO

Exibe informações básicas da GPU detectada pelo Windows, como:

* nome da GPU;
* memória informada pelo adaptador;
* versão do driver.

Esses dados são obtidos por meio do `Win32_VideoController`.

### GPU ENGINE - JSON

Exibe os contadores de uso dos motores da GPU, como 3D, Copy, Compute, Video Decode e outros mecanismos internos expostos pelo Windows.

A saída é convertida para JSON para evitar que o PowerShell corte valores longos, como pode acontecer com `Format-Table`.

Essa parte é útil para entender qual engine da GPU está realmente em uso.

### GPU MEMORY - JSON

Mostra os contadores completos de memória da GPU, incluindo:

* uso de memória dedicada;
* uso de memória compartilhada;
* limite de memória dedicada;
* limite de memória compartilhada.

Essa etapa ajuda a identificar se o Windows está expondo corretamente a VRAM ou a memória compartilhada, algo importante principalmente em GPUs integradas.

### GPU MEMORY - RESUMO GB

Gera um resumo mais legível em GB, mostrando:

* memória dedicada usada;
* memória compartilhada usada;
* total de memória usado;
* memória dedicada total;
* memória compartilhada total;
* total de memória GPU exibível.

Caso o Windows não retorne corretamente o limite de memória compartilhada, o script usa como fallback metade da memória RAM física do sistema.

## Como executar

No PowerShell, dentro da pasta do projeto:

```powershell
py diagnostico_gpu_taskmanager.py
```

ou:

```powershell
python diagnostico_gpu_taskmanager.py
```

## Quando usar

Use esse script quando o dashboard apresentar informações incorretas ou incompletas sobre a GPU, por exemplo:

* GPU aparecendo como não detectada;
* uso da GPU sempre em 0%;
* VRAM aparecendo como `N/A`;
* memória compartilhada incorreta;
* temperatura não sendo exibida;
* diferença entre os dados do dashboard e os dados do Gerenciador de Tarefas.

Esse diagnóstico ajuda a comparar os dados que o Windows fornece com os dados que o projeto está tentando mostrar no UNABOARD.

---

## Arquivos JavaScript

O JavaScript foi separado em módulos:

### `assets/js/core.js`

Contém funções base e o namespace global do dashboard.

Exemplo:

```javascript
window.UNABOARD
```

Também possui funções auxiliares, como escape de HTML.

---

### `assets/js/animacao.js`

Controla classes temporárias usadas durante redimensionamento e animações.

---

### `assets/js/responsivo.js`

Controla o ajuste de altura do iframe do Streamlit e o comportamento responsivo.

Ele evita que o painel fique com scroll extra ou altura quebrada dentro do `components.html`.

---

### `assets/js/monitor.js`

Controla a troca entre as páginas:

```text
Monitor <=> Rede
```

Também gerencia a animação horizontal de deslize.

---

### `assets/js/chatbot.js`

Controla o card de chatbot.

Ele:

- captura a mensagem digitada;
- envia para a API local;
- exibe a resposta;
- salva temporariamente a conversa no `sessionStorage`.

---

### `assets/js/app.js`

Arquivo de inicialização geral.

Ele chama os módulos necessários quando o dashboard carrega.

---

## Como executar o projeto

Os comandos abaixo consideram Windows com PowerShell.

Primeiro, entre na pasta do projeto:

```powershell
cd "C:\caminho\para\MoniSNMP"
```

---

## 1. Criar ambiente virtual

```powershell
py -m venv .MoniSNMP
```

Ative o ambiente:

```powershell
.\.MoniSNMP\Scripts\activate
```

Se o terminal mostrar algo parecido com isto, o ambiente está ativo:

```text
(.MoniSNMP) PS C:\...\MoniSNMP>
```

---

## 2. Instalar dependências

```powershell
py -m pip install -r requirements.txt
```

Dependências principais usadas pelo projeto:

- Streamlit
- psutil
- pandas
- plotly
- FastAPI
- Uvicorn
- google-genai
- streamlit-autorefresh, caso esteja disponível

---

## 3. Configurar a chave Gemini

O chatbot precisa de uma chave da API Gemini.

```text
chatbot.py
```

E preencher:

```python
API_KEY = "SUA_CHAVE_AQUI"
```

---

## 4. Rodar a API do chatbot

Abra um terminal e execute:

```powershell
py -m uvicorn chatbot_api:app --host 127.0.0.1 --port 8765
```

Se estiver funcionando, acesse:

```text
http://127.0.0.1:8765/health
```

Também é possível testar em:

```text
http://127.0.0.1:8765/docs
```

---

## 5. Rodar o dashboard Streamlit

Abra outro terminal, ative o mesmo ambiente virtual e execute:

```powershell
py -m streamlit run streamlit_app.py
```

O navegador deve abrir em um endereço parecido com:

```text
http://localhost:8501
```

---

## Fluxo de execução recomendado

Use dois terminais.

### Terminal 1: API do chatbot

```powershell
.\MoniSNMP\Scripts\activate
py -m uvicorn chatbot_api:app --host 127.0.0.1 --port 8765
```

### Terminal 2: Streamlit

```powershell
.\MoniSNMP\Scripts\activate
py -m streamlit run streamlit_app.py
```

---

## Como o histórico funciona

O histórico é salvo em:

```text
historico/historico.json
```

Quando o Streamlit carrega ou recarrega a página, ele chama:

```python
main.registrar_uma_vez()
```

Essa função:

1. coleta os dados atuais do sistema;
2. adiciona um novo registro ao histórico;
3. salva o arquivo `historico.json`;
4. retorna o mesmo snapshot para o dashboard.

Assim, os cards de Monitor, Rede e Processos usam o mesmo dado que acabou de ser registrado no histórico.

---

## Atualização do histórico

Nesta versão, o autorefresh automático fica desativado por padrão:

```python
REFRESH_MS = 0
```

Isso evita loops de refresh e problemas ao parar o Streamlit com `Ctrl + C`.

O histórico atualiza quando:

- você abre o painel;
- você aperta F5 ou Ctrl+R no navegador;
- o Streamlit reroda por alteração no código.

---

## Como confirmar que o histórico atualizou

Verifique o arquivo:

```text
historico/ultimo_refresh.txt
```

Ele deve conter algo como:

```text
Último refresh registrado pelo main.py
timestamp: ...
arquivo: historico/historico.json
itens_no_historico: ...
```

Se esse arquivo não mudar, provavelmente o Streamlit está rodando outro `streamlit_app.py` ou o projeto foi aberto em outra pasta.

---

## Rodar apenas o coletor

O `main.py` também pode ser executado sozinho:

```powershell
py main.py
```

Nesse modo, ele fica coletando dados em loop e salvando no histórico.

Para parar:

```text
Ctrl + C
```

Para uso normal do painel, não é obrigatório rodar o `main.py` separado, pois o Streamlit já chama `main.registrar_uma_vez()`.

---

## Parar o Streamlit

Normalmente:

```text
Ctrl + C
```

Se algum processo ficar preso na porta 8501, use:

```powershell
$pid8501 = (Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue).OwningProcess
Stop-Process -Id $pid8501 -Force
```

---

## Parar a API do chatbot

No terminal onde o Uvicorn está rodando:

```text
Ctrl + C
```

Se a porta 8765 ficar presa:

```powershell
$pid8765 = (Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue).OwningProcess
Stop-Process -Id $pid8765 -Force
```

---

## Problemas comuns

### O chatbot responde erro de chave não configurada

Verifique se a chave foi configurada em uma destas opções:

```powershell
$env:GEMINI_API_KEY="SUA_CHAVE_AQUI"
```

ou no arquivo:

```python
API_KEY = "SUA_CHAVE_AQUI"
```

Depois reinicie a API:

```powershell
py -m uvicorn chatbot_api:app --host 127.0.0.1 --port 8765
```

---

### O chatbot não responde no dashboard

Confirme se a API está ligada:

```text
http://127.0.0.1:8765/health
```

Se a API não estiver rodando, o card de chat não conseguirá enviar mensagens.

---

### O histórico não atualiza

Verifique:

```text
historico/ultimo_refresh.txt
```

Também confirme se você reiniciou o Streamlit depois de substituir os arquivos.

---

### O Ctrl + C não para o Streamlit

Isso pode acontecer se existir autorefresh em loop.

Nesta versão, o autorefresh fica desativado:

```python
REFRESH_MS = 0
```

Se ainda travar, finalize pela porta 8501:

```powershell
$pid8501 = (Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue).OwningProcess
Stop-Process -Id $pid8501 -Force
```

---

## Observações de segurança

Não publique sua chave da Gemini em repositório público.

Se a chave já foi enviada para GitHub, print ou ZIP compartilhado, gere uma nova chave e substitua a antiga.

---

## Resumo rápido

Para rodar o projeto completo:

```powershell
cd "C:\caminho\para\UNABOARD"
.\MoniSNMP\Scripts\activate
py -m pip install -r requirements.txt
```

Terminal 1:

```powershell
py -m uvicorn chatbot_api:app --host 127.0.0.1 --port 8765
```

Terminal 2:

```powershell
py -m streamlit run streamlit_app.py
```

Acesse:

```text
http://localhost:8501
```
