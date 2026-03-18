# 🧪 Guia de Teste - Detecção Automática de Segmento

## Como Testar a Detecção Automática

### 1. **Iniciar o Servidor**

```bash
python app_v2.py
```

Você verá:
```
🚀 Servidor iniciado em: http://127.0.0.1:5000
```

### 2. **Acessar a Interface**

Abra seu navegador e acesse: `http://127.0.0.1:5000`

### 3. **Fazer Upload de PDFs de Teste**

1. **Arraste os PDFs** de matrícula para a área de upload
2. Ou clique em **"Selecionar Arquivos"** e escolha os PDFs

### 4. **Verificar a Detecção**

Após o upload, você verá uma tabela com:
- ✅ **Nome do Aluno**: Extraído automaticamente
- ✅ **Tipo de Contrato**: **Detectado automaticamente** baseado no curso

**Verifique se o tipo de contrato está correto:**
- 📚 **Ed. Infantil / Fund. I / Fund. II** → Para alunos de Infantil, Fundamental I ou II
- 🎓 **Ensino Médio** → Para alunos do Ensino Médio

### 5. **Observar os Logs no Terminal**

No terminal onde o servidor está rodando, você verá:

**✅ Se detectou corretamente:**
- Nenhuma mensagem de aviso (detecção silenciosa)

**⚠️ Se não detectou:**
- `Aviso: Curso não detectado no PDF [nome_arquivo]`
- `Trecho encontrado: [texto extraído]...`
- `Usando padrão: infantil_fund1_fund2`

### 6. **Ajustar Manualmente (se necessário)**

Se a detecção automática não funcionar:
1. Na tabela, clique no **dropdown** do tipo de contrato
2. Selecione manualmente o tipo correto
3. Continue o processamento normalmente

### 7. **Processar os Contratos**

1. Clique em **"✅ Processar Todos (X)"**
2. Aguarde o processamento
3. Baixe os contratos gerados

---

## 🔍 Debug: Ver o que está sendo extraído

Se a detecção não estiver funcionando, você pode verificar o que o sistema está lendo do PDF:

### Opção 1: Ver os logs no terminal
Os logs mostram o trecho do texto onde o sistema procura por "CURSO".

### Opção 2: Testar manualmente um PDF

Crie um arquivo `test_extract.py`:

```python
import fitz
import sys

if len(sys.argv) < 2:
    print("Uso: python test_extract.py caminho_do_pdf")
    sys.exit(1)

pdf_path = sys.argv[1]
doc = fitz.open(pdf_path)
text = doc[0].get_text()
doc.close()

# Procurar por CURSO
import re
text_upper = text.upper()
if 'CURSO' in text_upper:
    idx = text_upper.find('CURSO')
    snippet = text_upper[max(0, idx-20):min(len(text_upper), idx+150)]
    print("Trecho encontrado:")
    print(snippet)
else:
    print("CURSO não encontrado no PDF")
    print("\nPrimeiras 500 caracteres do texto:")
    print(text[:500])
```

Execute:
```bash
python test_extract.py caminho/para/seu/pdf.pdf
```

---

## ✅ Checklist de Teste

- [ ] Servidor iniciado sem erros
- [ ] Interface carrega corretamente
- [ ] Upload de PDF funciona
- [ ] Nome do aluno é extraído
- [ ] **Tipo de contrato é detectado automaticamente**
- [ ] Tipo de contrato detectado está correto
- [ ] É possível editar manualmente o tipo de contrato
- [ ] Processamento funciona corretamente
- [ ] Contratos são gerados na pasta `contratos_prontos/`

---

## 🐛 Problemas Comuns

### Problema: "Curso não detectado"

**Possíveis causas:**
1. O PDF não contém o campo "CURSO" no formato esperado
2. O texto está em formato de imagem (PDF escaneado)
3. O formato do campo "CURSO" é diferente do esperado

**Solução:**
- Verifique os logs no terminal para ver o trecho extraído
- Edite manualmente o tipo de contrato na interface
- Se necessário, ajuste os padrões em `extract_course_segment()` no arquivo `app_v2.py`

### Problema: Tipo de contrato detectado incorretamente

**Solução:**
- Sempre revise a tabela antes de processar
- Edite manualmente se necessário
- O sistema permite edição mesmo após detecção automática

---

## 📊 Exemplos de Formatos Esperados

O sistema procura por padrões como:

- `CURSO: ENSINO FUNDAMENTAL II`
- `CURSO ENSINO MÉDIO`
- `CURSO: EDUCAÇÃO INFANTIL`
- `CURSO: ENSINO FUNDAMENTAL I`

E variações com/sem acentos, maiúsculas/minúsculas.

