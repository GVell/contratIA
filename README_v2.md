# 🎓 ContratIA v2.0 - Sistema de Processamento em Lote

Sistema inteligente para automação de contratos escolares com processamento em lote de múltiplos alunos.

## 📋 Índice

1. [Recursos](#recursos)
2. [Estrutura de Arquivos](#estrutura-de-arquivos)
3. [Instalação](#instalação)
4. [Configuração](#configuração)
5. [Como Usar](#como-usar)
6. [Troubleshooting](#troubleshooting)

---

## ✨ Recursos

### Principais Funcionalidades

- ✅ **Upload em Lote**: Arraste e solte múltiplos PDFs de matrícula de uma vez
- 🤖 **Extração Inteligente**: Detecta automaticamente o nome dos alunos nos PDFs
- 🎓 **Detecção Automática de Segmento**: Identifica automaticamente o curso/segmento (Infantil/Fundamental I-II ou Ensino Médio) do PDF
- 🎯 **Seleção de Contrato**: Escolha individual do tipo de contrato para cada aluno (com detecção automática pré-configurada)
- 📝 **Edição de Nomes**: Edite o nome final do arquivo antes de processar
- ⚡ **Processamento Rápido**: Transforma 5+ minutos por família em ~30 segundos
- 📊 **Relatório de Resultados**: Visualize sucessos e erros após processamento
- 💾 **Download Individual**: Baixe cada contrato processado separadamente

### Tipos de Contrato

1. **📚 Educação Infantil / Fundamental I / Fundamental II**
   - Arquivo: `Contrato_EI_EF1.pdf`
   - Para: Educação Infantil, Ensino Fundamental I e Ensino Fundamental II
   - **Detecção Automática**: O sistema identifica automaticamente se o aluno está em um desses segmentos

2. **🎓 Ensino Médio**
   - Arquivo: `Contrato_EF2_EM.pdf`
   - Para: Ensino Médio
   - **Detecção Automática**: O sistema identifica automaticamente se o aluno está no Ensino Médio

**Nota**: O sistema detecta automaticamente o segmento do aluno através do campo "CURSO" no PDF de matrícula. Você ainda pode editar manualmente o tipo de contrato na interface se necessário.

---

## 📁 Estrutura de Arquivos

```
seu_projeto/
│
├── app_v2.py                      # Backend Flask
├── requirements.txt               # Dependências Python
│
├── templates/
│   └── index_v2.html             # Interface HTML
│
├── static/
│   └── style_v2.css              # Estilos CSS
│
├── contratos_base/                # PDFs dos contratos base
│   ├── Contrato_EI_EF1.pdf       # Contrato Ed. Infantil/Fund. I
│   └── Contrato_EF2_EM.pdf       # Contrato Fund. II/Ensino Médio
│
├── uploads/                       # Pasta temporária (criada automaticamente)
└── contratos_prontos/            # Contratos finalizados (criada automaticamente)
```

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.7 ou superior
- pip (gerenciador de pacotes Python)

### Passo 1: Instalar Dependências

Crie um arquivo `requirements.txt`:

```txt
Flask==3.0.0
PyMuPDF==1.23.8
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

### Passo 2: Criar Estrutura de Pastas

```bash
mkdir templates static contratos_base
```

### Passo 3: Adicionar Contratos Base

Coloque os PDFs dos contratos base na pasta `contratos_base/`:

- `Contrato_EI_EF1.pdf` → Contrato para Ed. Infantil/Fund. I
- `Contrato_EF2_EM.pdf` → Contrato para Fund. II/Ensino Médio

⚠️ **IMPORTANTE**: Os nomes dos arquivos devem ser exatamente esses!

---

## ⚙️ Configuração

### Personalizar Pastas (Opcional)

No arquivo `app_v2.py`, você pode alterar os caminhos das pastas:

```python
# Configurações
UPLOAD_FOLDER = 'uploads'              # Pasta temporária
OUTPUT_FOLDER = 'contratos_prontos'    # Pasta de saída
CONTRACTS_FOLDER = 'contratos_base'    # Pasta dos contratos base
```

### Personalizar Extração de Nomes (Opcional)

Se seus PDFs têm um padrão diferente para o nome do aluno, edite a função `extract_student_name()` em `app_v2.py`:

```python
# Padrões para encontrar o nome do aluno
patterns = [
    r'Nome\s+do\s+Aluno[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
    r'Aluno[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
    # Adicione seus próprios padrões aqui
]
```

---

## 📖 Como Usar

### 1. Iniciar o Servidor

```bash
python app_v2.py
```

Você verá:

```
============================================================
🎓 ContratIA v2.0 - Sistema de Processamento em Lote
============================================================
📁 Pasta de contratos base: contratos_base
📤 Pasta de upload: uploads
📥 Pasta de saída: contratos_prontos
============================================================
🚀 Servidor iniciado em: http://127.0.0.1:5000
============================================================
```

### 2. Acessar a Interface

Abra seu navegador e acesse: `http://127.0.0.1:5000`

### 3. Processar Contratos

#### Passo 1: Upload dos PDFs

- Arraste os PDFs de matrícula para a área de upload
- Ou clique em "Selecionar Arquivos" e escolha múltiplos PDFs
- O sistema aceita apenas arquivos PDF

#### Passo 2: Revisar Dados Extraídos

O sistema mostrará uma tabela com:
- **Nome do Aluno**: Extraído automaticamente do PDF
- **Nome do Arquivo Final**: Nome sugerido para o contrato final (editável)
- **Tipo de Contrato**: Detectado automaticamente baseado no curso do aluno (pode ser editado manualmente se necessário)
  - 📚 Ed. Infantil / Fund. I / Fund. II
  - 🎓 Ensino Médio
- **Ações**: Remover aluno da lista se necessário

#### Passo 3: Processar

- Clique em "✅ Processar Todos (X)"
- Aguarde o processamento (geralmente 1-2 segundos por aluno)

#### Passo 4: Visualizar Resultados

O sistema mostrará:
- **Cards de Resumo**: Sucessos, Erros e Total
- **Lista de Resultados**: Cada contrato processado com botão de download

#### Passo 5: Download

- Clique em "⬇️ Baixar" para baixar cada contrato
- Ou acesse a pasta `contratos_prontos/` diretamente

### 4. Processar Novos Contratos

Clique em "🔄 Processar Novos Contratos" para reiniciar o processo.

---

## 🔧 Troubleshooting

### Problema: "Contrato base não encontrado"

**Solução**: 
- Verifique se os arquivos `Contrato_EI_EF1.pdf` e `Contrato_EF2_EM.pdf` estão na pasta `contratos_base/`
- Certifique-se que os nomes dos arquivos estão corretos (case-sensitive)

### Problema: Nome do aluno não detectado

**Solução**:
- O sistema usa regex para encontrar padrões como "Nome do Aluno:", "Aluno:", etc.
- Se seu PDF tem um formato diferente, edite a função `extract_student_name()` em `app_v2.py`
- Ou edite manualmente o nome na interface antes de processar

### Problema: Segmento/curso não detectado automaticamente

**Solução**:
- O sistema procura pelo campo "CURSO" no PDF de matrícula
- Se a detecção automática falhar, você pode editar manualmente o tipo de contrato na interface
- Verifique se o PDF contém o campo "CURSO" com o valor do segmento (ex: "ENSINO FUNDAMENTAL II", "ENSINO MÉDIO")
- Se necessário, edite a função `extract_course_segment()` em `app_v2.py` para ajustar os padrões de busca

### Problema: "Erro ao mesclar PDFs"

**Solução**:
- Verifique se o PDF de matrícula não está corrompido
- Tente abrir o PDF manualmente antes de fazer upload
- Verifique se há espaço em disco suficiente

### Problema: Downloads não funcionam

**Solução**:
- Verifique se a pasta `contratos_prontos/` existe
- Verifique permissões de escrita na pasta
- Tente acessar os arquivos diretamente na pasta

### Problema: "Port already in use"

**Solução**:
- Outro processo está usando a porta 5000
- Altere a porta no final de `app_v2.py`:
```python
app.run(debug=True, port=5001)  # Mudou para 5001
```

---

## 💡 Dicas de Uso

### Organização de Arquivos

1. **Nomeação Clara**: Os PDFs de matrícula devem ter o nome do aluno no conteúdo
2. **Lote por Turma**: Processe alunos da mesma turma juntos para facilitar
3. **Backup**: Mantenha backup dos PDFs originais

### Workflow Recomendado

```
1. Receber PDFs de matrícula via WhatsApp/Email
2. Baixar todos os PDFs em uma pasta
3. Abrir ContratIA v2.0
4. Upload em lote de todos os PDFs
5. Revisar e ajustar nomes/contratos
6. Processar tudo de uma vez
7. Fazer upload dos contratos no ClickSign
```

### Performance

- O sistema processa aproximadamente **30-40 alunos por minuto**
- Tempo médio: **1-2 segundos por aluno**
- Economia de tempo: **~90% em relação ao processo manual**

---

## 📊 Comparação: Versão 1.0 vs 2.0

| Recurso | v1.0 | v2.0 |
|---------|------|------|
| Upload | Um por vez | Múltiplos em lote |
| Extração de Nome | Manual | Automática |
| Processamento | Individual | Em lote |
| Tempo por Família | 5+ minutos | ~30 segundos |
| Preview | Não | Sim |
| Edição de Nomes | Limitada | Completa |
| Relatório Final | Não | Sim |

---

## 🔄 Migração da v1.0 para v2.0

Se você já usa a versão 1.0, siga estes passos:

1. **Backup dos Contratos Base**
   ```bash
   cp contratos_modelo/* contratos_base/
   ```

2. **Renomear Arquivos**
   - Renomeie seus contratos para seguir o padrão da v2.0

3. **Instalar Nova Dependência**
   ```bash
   pip install PyMuPDF==1.23.8
   ```

4. **Testar com Poucos Arquivos**
   - Faça um teste com 2-3 PDFs antes de processar em massa

---

## 📝 Notas Importantes

- ⚠️ Os arquivos temporários em `uploads/` são removidos após processamento
- ⚠️ Os contratos finais ficam salvos em `contratos_prontos/`
- ⚠️ O sistema NÃO valida se o tipo de contrato está correto - isso é responsabilidade do usuário
- ⚠️ PDFs corrompidos ou com formato inválido serão ignorados

---

## 🆘 Suporte

Se encontrar problemas ou tiver dúvidas:

1. Verifique se seguiu todos os passos de instalação
2. Consulte a seção de [Troubleshooting](#troubleshooting)
3. Verifique se os contratos base estão na pasta correta
4. Teste com um único PDF primeiro antes de processar em lote

---

## 📄 Licença

Sistema desenvolvido para uso interno do Colégio Anchieta.

---

## 🎉 Changelog

### v2.0 (Atual)
- ✨ Processamento em lote de múltiplos PDFs
- 🤖 Extração automática de nomes
- 📝 Edição de nomes finais
- 📊 Relatório de resultados
- 💾 Download individual de contratos

### v1.0
- Upload individual de PDFs
- Mesclagem simples de contratos
- Interface básica

---

**Desenvolvido com ❤️ para Colégio Anchieta**
