# WhatsApp Router - Sistema de Atendimento

Sistema de roteamento de mensagens do WhatsApp com interface web para confirmação de atendimento.

## 🔄 Novo Fluxo

1. **Cliente envia mensagem** → Recebe botões interativos (Comercial, Financeiro, Outros)
2. **Cliente clica no botão** → Sistema pede que escreva a mensagem
3. **Cliente envia mensagem(ns)** → Sistema:
   - Salva no DB temporário (`pending_responses`)
   - Notifica cliente: "Responsável irá responder em breve"
   - Envia **link** para o responsável do setor
4. **Responsável clica no link** → Abre interface web mostrando:
   - Cliente
   - Setor
   - Todas as mensagens
   - Botão "Responder Cliente"
5. **Responsável clica em "Responder"** → Sistema:
   - Marca como `respondida: true` no DB
   - Envia mensagem via WhatsApp: "✅ CONVERSA INICIADA"
   - Fornece link direto para WhatsApp do cliente
6. **Limpeza automática** → Após 1 dia, registros são deletados

## 📂 Estrutura

```
wpp-router/
├── app/
│   ├── client.py          # Funções de envio WhatsApp
│   └── db.py              # Conexões MongoDB
├── templates/
│   └── response.html      # Interface web para responsável
├── main.py                # FastAPI app principal
├── requirements.txt
└── .env
```

## 🗄️ Collections do MongoDB

### `sessions`
```json
{
  "phone": "5549988883173",
  "step": "menu|message",
  "choice": "comercial|financeiro|outros",
  "last_menu": ISODate()
}
```

### `sellers`
```json
{
  "phone": "5549999999999",
  "online": true,
  "sector": "comercial|financeiro|outros",
  "lastAssigned": ISODate()
}
```

### `leads`
```json
{
  "client": "5549988883173",
  "seller": "5549999999999",
  "sector": "comercial",
  "status": "pending|closed",
  "created_at": ISODate()
}
```

### `pending_responses` (NOVO)
```json
{
  "client": "5549988883173",
  "seller": "5549999999999",
  "sector": "comercial",
  "messages": [
    {"text": "Olá, preciso de ajuda", "timestamp": ISODate()},
    {"text": "Estou com dúvida sobre produto X", "timestamp": ISODate()}
  ],
  "respondida": false,
  "created_at": ISODate(),
  "last_update": ISODate(),
  "responded_at": ISODate() // quando confirmado
}
```

## 🚀 Instalação

1. **Clone e instale dependências**
```bash
pip install -r requirements.txt
```

2. **Configure o .env**
```env
MONGO_URI=mongodb://localhost:27017
WHATSAPP_TOKEN=seu_token_aqui
PHONE_NUMBER_ID=seu_phone_id_aqui
VERIFY_TOKEN=seu_verify_token_aqui
SERVER_URL=https://seu-dominio.com
```

3. **Crie sellers no MongoDB**
```javascript
db.sellers.insertMany([
  {
    phone: "5549999999999",
    online: true,
    sector: "comercial",
    lastAssigned: new Date()
  },
  {
    phone: "5549888888888",
    online: true,
    sector: "financeiro",
    lastAssigned: new Date()
  }
])
```

4. **Execute o servidor**
```bash
uvicorn main:app --reload
```

## 📡 Endpoints

- `GET /webhook` - Verificação do webhook
- `POST /webhook` - Recebe mensagens do WhatsApp
- `GET /response/{request_id}` - Interface web para responsável
- `POST /confirm-response/{request_id}` - Confirma atendimento
- `DELETE /cleanup-old-responses` - Limpa registros antigos (criar cron job)

## 🔧 Configuração do Webhook no Meta

1. Acesse o Meta for Developers
2. WhatsApp → Configuration → Webhook
3. Callback URL: `https://seu-dominio.com/webhook`
4. Verify Token: (mesmo do .env)
5. Subscribe to: `messages`

## 🔄 Limpeza Automática

Configure um cron job para limpar registros antigos diariamente:

```bash
# Exemplo: Executar todos os dias às 2h da manhã
0 2 * * * curl -X DELETE https://seu-dominio.com/cleanup-old-responses
```

Ou use um serviço como EasyCron, cron-job.org, etc.

## 📱 Teste Rápido

1. Envie mensagem para o número do bot
2. Clique em "Comercial"
3. Escreva "Teste de mensagem"
4. O responsável receberá um link
5. Clique no link e confirme
6. Receberá "CONVERSA INICIADA" no WhatsApp

## 🐛 Debug

Todos os prints estão no console do servidor. Procure por:
- 📱 Phone normalized
- 🔘 Interactive button clicked
- 🔍 Lead check
- 👤 Session
- ✅ Lead created
- 📝 Pending response created
