

from google import genai
from google.genai import types

from dados.cpu import get_cpu
from dados.memoria import get_memoria
from dados.gpu import get_gpu
from dados.rede import get_rede
from dados.disco import get_disco
from dados.processos import get_processos

try:
    from dados.rede_qualidade import get_ping, get_packet_loss, get_jitter
except ImportError:
    get_ping = get_packet_loss = get_jitter = None

API_KEY = "AQ.Ab8RN6Ih8B_I0LhcQah_LhhWs5A5YU7UZq_m-BgBCrWh2oVUhQ"
client = genai.Client(api_key=API_KEY)

INSTRUCAO_SISTEMA = """
Você é o UNABOARD, um Assistente de TI avançado integrado a um painel de monitoramento.
Sempre que o usuário fizer uma pergunta, você receberá um bloco [DADOS DO SISTEMA NESTE MOMENTO].
Use essas informações ativas da máquina para diagnosticar problemas.
Seja direto, analítico, técnico e responda em português brasileiro, porém de forma que seja fácil de entender, tente apresentar soluções.
"""

chat_session = client.chats.create(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        system_instruction=INSTRUCAO_SISTEMA,
        temperature=0.2,
    )
)

def gerar_relatorio_hardware_atual():
    try:
        cpu_uso = get_cpu()
        mem = get_memoria()
        gpu = get_gpu()
        rede = get_rede()
        disco = get_disco()
        processos = get_processos()
        
        ping = get_ping() if get_ping else "N/A"
        loss = get_packet_loss() if get_packet_loss else "N/A"
        jitter = get_jitter() if get_jitter else "N/A"
        
        lista_processos = ""
        for p in processos[:5]: 
            lista_processos += f"  - {p['nome']} (PID: {p['pid']}) | CPU: {p['cpu']}% | RAM: {p['memoria_mb']} MB\n"

        relatorio = f"""
[DADOS DO SISTEMA NESTE MOMENTO]

[HARDWARE GERAL]
- CPU: {cpu_uso}%
- RAM: {mem['used']} GB / {mem['total']} GB ({mem['percent']}%)
- Disco (/): {disco['used']} GB / {disco['total']} GB ({disco['percent']}%)
- GPU: {gpu.get('nome', 'N/A')}
- Uso GPU: {gpu.get('uso_gpu', 0)}% | VRAM Usada: {gpu.get('memoria_usada_gb', 0)} GB
- Temp GPU: {gpu.get('temperatura', 'N/A')}°C

[REDE E QUALIDADE]
- Tráfego: Down {rede.get('download_mbps', 0)} Mbps | Up {rede.get('upload_mbps', 0)} Mbps
- Ping: {ping} ms | Packet Loss: {loss}% | Jitter: {jitter} ms

[TOP 5 PROCESSOS CONSUMINDO RECURSOS]
{lista_processos}
"""
        return relatorio
    except Exception as e:
        return f"[AVISO: Falha ao coletar dados do hardware no momento: {e}]"

def enviar_mensagem_com_hardware(mensagem_usuario):
    
    hardware_atual = gerar_relatorio_hardware_atual()

    prompt_injetado = f"{hardware_atual}\n\nPergunta do usuário: {mensagem_usuario}"
    
    resposta = chat_session.send_message(prompt_injetado)
    
    return resposta.text