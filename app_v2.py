from flask import Flask, render_template, request, jsonify, send_file
import fitz  # PyMuPDF
import os
import re
from pathlib import Path
from datetime import datetime
import pytesseract
from PIL import Image

# Configurar caminho do Tesseract (Windows)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Configurar pasta de dados de idioma do Tesseract
TESSDATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tessdata')
os.environ['TESSDATA_PREFIX'] = TESSDATA_PATH

app = Flask(__name__)

# Configurações
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'contratos_prontos'
CONTRACTS_FOLDER = 'contratos_base'

# Criar pastas se não existirem
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, CONTRACTS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Mapeamento dos contratos base
CONTRACTS = {
    'infantil_fund1_fund2': 'Contrato_EI_EF1.pdf',  # Educação Infantil, Fundamental I e Fundamental II
    'medio': 'Contrato_EF2_EM.pdf'                   # Ensino Médio
}

def extract_text_top_region(pdf_path, page_index=0):
    """
    Extrai via OCR o texto da região superior da página (título do
    formulário + campo "Aluno(a):"). O texto puro extraído por PyMuPDF
    nesses PDFs vem corrompido (fonte sem mapa Unicode), então OCR é o
    único método confiável aqui — mesma razão pela qual o segmento/curso
    já dependia de OCR.
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_index]

        page_rect = page.rect
        # Região superior o bastante para cobrir título + campo Aluno(a),
        # sem entrar nos dados dos pais/responsável logo abaixo.
        clip_rect = fitz.Rect(0, 0, page_rect.width, page_rect.height * 0.28)

        zoom = 2.2
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=clip_rect)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        custom_config = r'--psm 6 --oem 3'
        text = pytesseract.image_to_string(img, lang='por', config=custom_config)

        doc.close()
        return text
    except Exception as e:
        print(f"  [OCR] Erro ao extrair topo da página {page_index}: {str(e)}")
        return ""


def is_new_requerimento_page(top_text):
    """
    Uma página inicia um novo requerimento quando traz o título do
    formulário ou o campo Aluno/Aluna. Páginas sem nenhum dos dois são
    tratadas como continuação do requerimento anterior.
    """
    if not top_text:
        return False
    return bool(re.search(r'REQUERIMENTO|Alun[oa0]\s*[:\-]', top_text, re.IGNORECASE))


def extract_student_name_from_text(top_text):
    """
    Extrai o nome do aluno a partir do texto OCR do topo da página,
    lendo o campo "Aluno:" / "Aluna:".
    """
    if not top_text:
        return None

    match = re.search(r'Alun[oa0]\s*[:\-]?\s*([^\n]+)', top_text, re.IGNORECASE)
    if not match:
        return None

    name = match.group(1)
    # Cortar caso o OCR tenha colado o próximo campo na mesma linha
    name = re.split(r'G[êeé]nero|N[ºo°]|Data\s+de|Prontu', name, flags=re.IGNORECASE)[0]
    name = re.sub(r'\s+', ' ', name).strip(' :-.')

    if len(name) < 5:
        return None

    return name.upper()


def sanitize_name_from_filename(pdf_path):
    """
    Fallback quando o OCR não consegue ler o nome do aluno: deriva um nome
    a partir do nome do arquivo.
    """
    filename = os.path.basename(pdf_path)
    filename = re.sub(r'\.pdf$', '', filename, flags=re.IGNORECASE)
    filename = filename.replace('_', ' ')
    return filename.strip()


def detect_requerimento_blocks(pdf_path):
    """
    Divide um PDF em blocos, um por aluno/requerimento.

    A secretaria agora entrega os requerimentos de todos os irmãos de uma
    família já juntos em um único arquivo (um requerimento por página), em
    vez de um arquivo por aluno como antes. Esta função identifica onde
    cada requerimento começa dentro do arquivo, para que nome, segmento e
    contrato sejam detectados individualmente por aluno — e não apenas uma
    vez para o arquivo inteiro.

    Retorna uma lista de blocos: {page_start, page_end, top_text}
    (page_start/page_end são 0-indexed e inclusivos).
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    blocks = []
    current = None

    for i in range(total_pages):
        top_text = extract_text_top_region(pdf_path, i)

        if current is None or is_new_requerimento_page(top_text):
            if current is not None:
                blocks.append(current)
            current = {'page_start': i, 'page_end': i, 'top_text': top_text}
        else:
            # Continuação do requerimento anterior (formulário com mais de
            # uma página) — estende o bloco atual em vez de abrir um novo.
            current['page_end'] = i

    if current is not None:
        blocks.append(current)

    return blocks

def extract_text_with_ocr(pdf_path, page_index=0):
    """
    Extrai texto do PDF usando OCR (Optical Character Recognition).
    OTIMIZADO: Processa apenas a metade inferior da página (onde está a tabela CURSO)
    """
    try:
        print(f"  [OCR] Iniciando extração com OCR (página {page_index})...")
        doc = fitz.open(pdf_path)
        page = doc[page_index]

        # OTIMIZAÇÃO 1: Processar apenas metade inferior da página
        # A tabela CURSO geralmente está no final do requerimento
        page_rect = page.rect
        half_height = page_rect.height / 2

        # Definir clip para processar apenas a metade inferior
        clip_rect = fitz.Rect(0, half_height, page_rect.width, page_rect.height)

        # Resolução do OCR: 1.5x provou ser insuficiente para ler a tabela
        # "CURSO" em alguns requerimentos (fonte pequena), causando falha
        # silenciosa na detecção e um fallback incorreto para o tipo padrão.
        # 2.2x mantém boa legibilidade em todos os PDFs testados.
        zoom = 2.2
        mat = fitz.Matrix(zoom, zoom)

        # Renderizar apenas a região inferior
        pix = page.get_pixmap(matrix=mat, clip=clip_rect)

        # Converter para PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # OTIMIZAÇÃO 3: Configurar Tesseract para texto simples (mais rápido)
        # PSM 6 = assume bloco de texto uniforme (ideal para tabelas)
        custom_config = r'--psm 6 --oem 3'
        text = pytesseract.image_to_string(img, lang='por', config=custom_config)

        doc.close()
        print(f"  [OCR] Texto extraído: {len(text)} caracteres")
        return text

    except Exception as e:
        print(f"  [OCR] Erro ao extrair com OCR: {str(e)}")
        return ""

def extract_course_segment(pdf_path, page_index=0):
    """
    Extrai o curso/segmento do PDF de matrícula usando OCR.
    Retorna o tipo de contrato: 'infantil_fund1_fund2' ou 'medio'

    Método principal: OCR (funciona com todos os PDFs de requerimento)
    Fallback: PyMuPDF (caso OCR falhe)

    page_index: página (0-indexed) dentro do PDF onde está este requerimento
    específico. Um mesmo arquivo pode conter vários requerimentos (irmãos),
    um por página, então isso NUNCA deve ficar hardcoded em 0.
    """
    doc = None
    try:
        print(f"\n[DEBUG] Analisando: {os.path.basename(pdf_path)} (página {page_index})")

        # MÉTODO PRINCIPAL: OCR (mais confiável para PDFs de requerimento)
        print("  [OCR] Usando OCR para extração...")
        ocr_text = extract_text_with_ocr(pdf_path, page_index)

        if ocr_text and len(ocr_text) > 0:
            ocr_upper = ocr_text.upper()

            # Procurar CURSO no texto do OCR
            if 'CURSO' in ocr_upper:
                print(f"  [OCR] Campo 'CURSO' encontrado")
                lines = ocr_upper.split('\n')

                for i, line in enumerate(lines):
                    if 'CURSO' in line:
                        print(f"  [OCR] Linha: '{line.strip()}'")

                        # Verificar se MÉDIO está na mesma linha
                        if re.search(r'M[EÉ]DIO', line):
                            print(f"  [OCR] ENSINO MEDIO detectado!")
                            return 'medio'

                        # Verificar FUNDAMENTAL ou INFANTIL
                        if re.search(r'FUNDAMENTAL|INFANTIL', line):
                            curso = re.search(r'(FUNDAMENTAL|INFANTIL)', line).group(0)
                            print(f"  [OCR] {curso} detectado!")
                            return 'infantil_fund1_fund2'

                        # Se não encontrou na mesma linha, verificar próximas linhas
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            print(f"  [OCR] Proxima linha: '{next_line}'")

                            if re.search(r'M[EÉ]DIO', next_line):
                                print(f"  [OCR] ENSINO MEDIO detectado (linha seguinte)!")
                                return 'medio'

                            if re.search(r'FUNDAMENTAL|INFANTIL', next_line):
                                curso = re.search(r'(FUNDAMENTAL|INFANTIL)', next_line).group(0)
                                print(f"  [OCR] {curso} detectado (linha seguinte)!")
                                return 'infantil_fund1_fund2'
                        break

            # Busca ampla no texto OCR
            if re.search(r'ENSINO\s+M[EÉ]DIO|M[EÉ]DIO', ocr_upper):
                print(f"  [OCR] ENSINO MEDIO detectado (busca ampla)!")
                return 'medio'

            if re.search(r'FUNDAMENTAL|INFANTIL', ocr_upper):
                print(f"  [OCR] FUNDAMENTAL/INFANTIL detectado (busca ampla)!")
                return 'infantil_fund1_fund2'

        # FALLBACK: Se OCR falhou, tentar PyMuPDF
        print("  [FALLBACK] OCR nao encontrou. Tentando PyMuPDF...")
        doc = fitz.open(pdf_path)
        text = ""
        page = None

        if len(doc) > page_index:
            page = doc[page_index]
            try:
                text = page.get_text("text")
            except:
                text = page.get_text()

        # Busca simples no texto extraído via PyMuPDF
        text_upper = text.upper()
        if 'CURSO' in text_upper:
            print(f"  [FALLBACK] Campo 'CURSO' encontrado via PyMuPDF")
            lines = text_upper.split('\n')

            for i, line in enumerate(lines):
                if 'CURSO' in line and 'CURSO:' not in line:  # Linha que contém CURSO (formato tabela)
                    print(f"  [TABELA] Linha: '{line.strip()}'")

                    # Verificar se o curso está na mesma linha (após múltiplos espaços)
                    if re.search(r'M[ÉE]DIO', line):
                        print(f"  [DETECTADO] ENSINO MEDIO")
                        if doc:
                            doc.close()
                        return 'medio'
                    elif re.search(r'FUNDAMENTAL|INFANTIL', line):
                        curso_encontrado = re.search(r'(FUNDAMENTAL|INFANTIL)', line).group(0)
                        print(f"  [DETECTADO] {curso_encontrado}")
                        if doc:
                            doc.close()
                        return 'infantil_fund1_fund2'

                    # Se não encontrou na mesma linha, verificar linha seguinte
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        print(f"  [PROXIMA] Verificando: '{next_line}'")
                        if re.search(r'M[ÉE]DIO', next_line):
                            print(f"  [DETECTADO] ENSINO MEDIO (linha seguinte)")
                            if doc:
                                doc.close()
                            return 'medio'
                        elif re.search(r'FUNDAMENTAL|INFANTIL', next_line):
                            curso_encontrado = re.search(r'(FUNDAMENTAL|INFANTIL)', next_line).group(0)
                            print(f"  [DETECTADO] {curso_encontrado} (linha seguinte)")
                            if doc:
                                doc.close()
                            return 'infantil_fund1_fund2'
                    break

        # Normalizar o texto: remover espaços extras mas manter estrutura
        text_normalized = re.sub(r'\s+', ' ', text)
        text_upper = text_normalized.upper()

        # Se não encontrou CURSO no texto simples, tentar extração baseada em coordenadas (para tabelas)
        if 'CURSO' not in text_upper and page is not None:
            try:
                # Usar get_text("dict") para obter texto com coordenadas
                text_dict = page.get_text("dict")
                curso_y = None
                curso_x_end = None
                
                # Procurar pelo bloco que contém "CURSO" e obter suas coordenadas
                for block in text_dict.get("blocks", []):
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line.get("spans", []):
                                span_text = span.get("text", "").upper()
                                if "CURSO" in span_text:
                                    bbox = span.get("bbox", [0, 0, 0, 0])
                                    curso_y = bbox[1]  # Coordenada Y superior
                                    curso_x_end = bbox[2]  # Coordenada X final (fim da palavra CURSO)
                                    break
                            if curso_y is not None:
                                break
                    if curso_y is not None:
                        break
                
                # Se encontrou CURSO, procurar o valor na mesma linha (mesma Y) mas à direita (X maior)
                if curso_y is not None:
                    tolerance_y = 15  # Tolerância de 15 pixels para considerar mesma linha
                    candidates = []
                    
                    # Coletar todos os spans que estão na mesma linha (ou próxima) e à direita do CURSO
                    for block in text_dict.get("blocks", []):
                        if "lines" in block:
                            for line in block["lines"]:
                                line_bbox = line.get("bbox", [0, 0, 0, 0])
                                line_y = line_bbox[1]
                                
                                # Se está na mesma linha (dentro da tolerância)
                                if abs(line_y - curso_y) <= tolerance_y:
                                    for span in line.get("spans", []):
                                        span_bbox = span.get("bbox", [0, 0, 0, 0])
                                        span_x_start = span_bbox[0]
                                        span_text = span.get("text", "").strip()
                                        
                                        # Se está à direita do CURSO (ou próximo horizontalmente)
                                        if span_x_start >= curso_x_end - 50:  # Permitir pequena sobreposição
                                            # Verificar se contém palavras-chave de curso
                                            span_upper = span_text.upper()
                                            if any(keyword in span_upper for keyword in ["ENSINO", "FUNDAMENTAL", "INFANTIL", "MÉDIO", "MEDIO", "EDUCAÇÃO", "EDUCACAO"]):
                                                candidates.append((span_x_start, span_text))
                    
                    # Ordenar candidatos por posição X (da esquerda para direita) e pegar o primeiro
                    if candidates:
                        candidates.sort(key=lambda x: x[0])
                        course_value = candidates[0][1]
                        # Adicionar ao texto para processamento normal
                        text += " CURSO " + course_value
                        text_upper = text.upper()
                        print(f"  [OK] Curso encontrado via extração por coordenadas: {course_value}")
            except Exception as e:
                # Se falhar, continuar com o método normal
                print(f"  Aviso: Erro na extração por coordenadas: {str(e)}")
        
        # Re-normalizar o texto após possível adição de texto via coordenadas
        if text:
            text_normalized = re.sub(r'\s+', ' ', text)
            text_upper = text_normalized.upper()
        
        # Padrões mais específicos para encontrar o curso na tabela
        # Procura por "CURSO" seguido de dois pontos, espaço ou quebra, e depois o valor
        patterns = [
            # Padrão: CURSO: ENSINO MÉDIO / CURSO ENSINO MÉDIO
            r'CURSO[:\s]+(ENSINO\s+M[ÉE]DIO)',
            # Padrão: CURSO: EDUCAÇÃO INFANTIL
            r'CURSO[:\s]+(EDUCA[ÇC][AÃ]O\s+INFANTIL)',
            # Padrão: CURSO: ENSINO FUNDAMENTAL I
            r'CURSO[:\s]+(ENSINO\s+FUNDAMENTAL\s+I\b)',
            # Padrão: CURSO: ENSINO FUNDAMENTAL II
            r'CURSO[:\s]+(ENSINO\s+FUNDAMENTAL\s+II\b)',
            # Padrão: CURSO: FUNDAMENTAL I
            r'CURSO[:\s]+(FUNDAMENTAL\s+I\b)',
            # Padrão: CURSO: FUNDAMENTAL II
            r'CURSO[:\s]+(FUNDAMENTAL\s+II\b)',
            # Padrão mais flexível: qualquer coisa após CURSO que contenha as palavras-chave
            r'CURSO[:\s]+([^:]*?ENSINO\s+M[ÉE]DIO[^:]*?)',
            r'CURSO[:\s]+([^:]*?FUNDAMENTAL[^:]*?)',
            r'CURSO[:\s]+([^:]*?INFANTIL[^:]*?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_upper, re.IGNORECASE)
            if match:
                course = match.group(1).upper()
                
                # Mapear o curso para o tipo de contrato
                if 'MÉDIO' in course or 'MEDIO' in course:
                    print(f"[OK] Curso detectado: {course} -> Ensino Médio")
                    if doc:
                        doc.close()
                    return 'medio'
                elif 'INFANTIL' in course or 'FUNDAMENTAL' in course:
                    print(f"[OK] Curso detectado: {course} -> Infantil/Fund. I-II")
                    if doc:
                        doc.close()
                    return 'infantil_fund1_fund2'
        
        # Busca alternativa: procurar diretamente por palavras-chave próximas a "CURSO"
        # Procura em uma janela maior (até 200 caracteres) para capturar tabelas
        if 'CURSO' in text_upper:
            idx = text_upper.find('CURSO')
            # Pegar uma região maior ao redor do CURSO (até 200 caracteres após)
            curso_region = text_upper[idx:min(len(text_upper), idx+200)]
            
            # Procurar por padrões na região do CURSO
            if re.search(r'\bENSINO\s+M[ÉE]DIO\b', curso_region, re.IGNORECASE):
                print(f"[OK] Curso detectado na região do CURSO: ENSINO MÉDIO")
                if doc:
                    doc.close()
                return 'medio'
            elif re.search(r'\b(EDUCA[ÇC][AÃ]O\s+INFANTIL|ENSINO\s+FUNDAMENTAL|FUNDAMENTAL)\b', curso_region, re.IGNORECASE):
                match_fund = re.search(r'(EDUCA[ÇC][AÃ]O\s+INFANTIL|ENSINO\s+FUNDAMENTAL|FUNDAMENTAL)', curso_region, re.IGNORECASE)
                if match_fund:
                    print(f"[OK] Curso detectado na região do CURSO: {match_fund.group(0)}")
                if doc:
                    doc.close()
                return 'infantil_fund1_fund2'
            
            # Se CURSO foi encontrado mas o valor não está próximo no texto, tentar extração por coordenadas
            if page is not None:
                try:
                    text_dict = page.get_text("dict")
                    curso_y = None
                    curso_x_end = None
                    
                    # Procurar pelo bloco que contém "CURSO" e obter suas coordenadas
                    for block in text_dict.get("blocks", []):
                        if "lines" in block:
                            for line in block["lines"]:
                                for span in line.get("spans", []):
                                    span_text = span.get("text", "").upper()
                                    if "CURSO" in span_text:
                                        bbox = span.get("bbox", [0, 0, 0, 0])
                                        curso_y = bbox[1]
                                        curso_x_end = bbox[2]
                                        break
                                if curso_y is not None:
                                    break
                        if curso_y is not None:
                            break
                    
                    # Se encontrou CURSO, procurar o valor na mesma linha
                    if curso_y is not None:
                        tolerance_y = 15
                        candidates = []
                        
                        for block in text_dict.get("blocks", []):
                            if "lines" in block:
                                for line in block["lines"]:
                                    line_bbox = line.get("bbox", [0, 0, 0, 0])
                                    line_y = line_bbox[1]
                                    
                                    if abs(line_y - curso_y) <= tolerance_y:
                                        for span in line.get("spans", []):
                                            span_bbox = span.get("bbox", [0, 0, 0, 0])
                                            span_x_start = span_bbox[0]
                                            span_text = span.get("text", "").strip()
                                            
                                            if span_x_start >= curso_x_end - 50:
                                                span_upper = span_text.upper()
                                                if any(keyword in span_upper for keyword in ["ENSINO", "FUNDAMENTAL", "INFANTIL", "MÉDIO", "MEDIO", "EDUCAÇÃO", "EDUCACAO"]):
                                                    candidates.append((span_x_start, span_text))
                        
                        if candidates:
                            candidates.sort(key=lambda x: x[0])
                            course_value = candidates[0][1]
                            course_upper = course_value.upper()
                            
                            if 'MÉDIO' in course_upper or 'MEDIO' in course_upper:
                                print(f"[OK] Curso detectado via coordenadas: {course_value} -> Ensino Médio")
                                if doc:
                                    doc.close()
                                return 'medio'
                            elif 'INFANTIL' in course_upper or 'FUNDAMENTAL' in course_upper:
                                print(f"[OK] Curso detectado via coordenadas: {course_value} -> Infantil/Fund. I-II")
                                if doc:
                                    doc.close()
                                return 'infantil_fund1_fund2'
                except Exception as e:
                    pass  # Se falhar, continuar com busca ampla
        
        # Busca mais ampla no texto inteiro (fallback)
        if re.search(r'\bENSINO\s+M[ÉE]DIO\b', text_upper, re.IGNORECASE):
            print(f"[OK] Curso detectado (busca ampla): ENSINO MÉDIO")
            if doc:
                doc.close()
            return 'medio'
        elif re.search(r'\b(EDUCA[ÇC][AÃ]O\s+INFANTIL|ENSINO\s+FUNDAMENTAL|FUNDAMENTAL)\b', text_upper, re.IGNORECASE):
            match_fund = re.search(r'(EDUCA[ÇC][AÃ]O\s+INFANTIL|ENSINO\s+FUNDAMENTAL|FUNDAMENTAL)', text_upper, re.IGNORECASE)
            if match_fund:
                print(f"[OK] Curso detectado (busca ampla): {match_fund.group(0)}")
            if doc:
                doc.close()
            return 'infantil_fund1_fund2'
        
        # Se não encontrar, retornar padrão (infantil_fund1_fund2)
        # Debug: mostrar trecho do texto onde deveria estar o CURSO
        debug_snippet = ""
        if 'CURSO' in text_upper:
            idx = text_upper.find('CURSO')
            debug_snippet = text_upper[max(0, idx):min(len(text_upper), idx+150)]
            print(f"Aviso: Curso não detectado no PDF {os.path.basename(pdf_path)}")
            print(f"  Trecho encontrado: {debug_snippet}")
            print(f"  Tentando busca alternativa...")
            
            # Tentar buscar na linha seguinte ou próxima ao CURSO
            # Procurar por padrões mais flexíveis na região do CURSO
            curso_region = text_upper[max(0, idx-50):min(len(text_upper), idx+200)]
            
            # Procurar por palavras-chave próximas ao CURSO
            if re.search(r'ENSINO\s+M[ÉE]DIO', curso_region, re.IGNORECASE):
                print(f"  [OK] Detectado: ENSINO MÉDIO (busca alternativa)")
                if doc:
                    doc.close()
                return 'medio'
            elif re.search(r'FUNDAMENTAL', curso_region, re.IGNORECASE):
                print(f"  [OK] Detectado: FUNDAMENTAL (busca alternativa)")
                if doc:
                    doc.close()
                return 'infantil_fund1_fund2'
            elif re.search(r'INFANTIL', curso_region, re.IGNORECASE):
                print(f"  [OK] Detectado: INFANTIL (busca alternativa)")
                if doc:
                    doc.close()
                return 'infantil_fund1_fund2'

        # Se nem OCR nem PyMuPDF conseguiram detectar, NÃO adivinhar.
        # Um default silencioso aqui já causou contratos com o tipo errado
        # anexado sem que ninguém percebesse. Sinalizar como não detectado
        # para que a interface force a revisão manual desse aluno.
        print(f"  [AVISO] Nao foi possivel detectar tipo de contrato. Marcando para revisao manual.")
        doc.close()
        return None

    except Exception as e:
        print(f"Erro ao extrair curso: {str(e)}")
        # Não adivinhar em caso de erro: sinalizar para revisão manual.
        try:
            doc.close()
        except:
            pass
        return None

def append_student_to_doc(output_doc, enrollment_path, page_start, page_end, contract_type):
    """
    Anexa ao PDF de saída (já aberto) as páginas de UM requerimento
    específico (page_start..page_end, inclusive) seguidas do contrato base
    correspondente ao segmento daquele aluno.

    Usada tanto para gerar um contrato individual quanto para concatenar
    vários alunos (irmãos) em um único PDF final — nesse caso, cada aluno
    entra com seu próprio requerimento + seu próprio contrato, na ordem em
    que aparecem no arquivo original, permitindo tipos de contrato
    diferentes entre irmãos (ex.: um no Fundamental, outro no Médio).
    """
    contract_path = os.path.join(CONTRACTS_FOLDER, CONTRACTS[contract_type])
    if not os.path.exists(contract_path):
        raise Exception(f"Contrato base não encontrado: {contract_path}")

    enrollment_doc = fitz.open(enrollment_path)
    output_doc.insert_pdf(enrollment_doc, from_page=page_start, to_page=page_end)
    enrollment_doc.close()

    contract_doc = fitz.open(contract_path)
    output_doc.insert_pdf(contract_doc)
    contract_doc.close()


def build_pdf(items, output_path):
    """
    Constrói um PDF final a partir de uma lista de itens (cada um com
    enrollment_path, page_start, page_end, contract_type) e salva em
    output_path. Usada tanto para um único aluno (lista de 1 item) quanto
    para um grupo de irmãos mesclados (lista com vários itens).
    """
    output_doc = fitz.open()
    for item in items:
        append_student_to_doc(
            output_doc,
            item['enrollment_path'],
            item['page_start'],
            item['page_end'],
            item['contract_type']
        )
    output_doc.save(output_path)
    output_doc.close()

def sanitize_filename(name):
    """
    Remove caracteres inválidos do nome do arquivo, preservando a extensão.

    Bug histórico: a versão anterior removia o "." junto com os outros
    caracteres especiais, então "Fulano.pdf" virava "Fulanopdf" — sem
    extensão. Isso explica os nomes finais estranhos ("...GONÇALVESpdf")
    encontrados em contratos_prontos/ de processamentos antigos.
    """
    base, ext = os.path.splitext(name)
    base = re.sub(r'[^\w\s-]', '', base)
    base = re.sub(r'[\s]+', '_', base)
    return base + ext.lower()

@app.route('/')
def index():
    return render_template('index_v2.html')

def format_names_list(names):
    """ 'A' | 'A e B' | 'A, B e C' """
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} e {names[1]}"
    return ", ".join(names[:-1]) + f" e {names[-1]}"


@app.route('/upload', methods=['POST'])
def upload_files():
    """
    Recebe PDFs de requerimento e extrai informações.

    Cada arquivo enviado forma um "grupo" (uma família). A secretaria hoje
    já entrega os requerimentos de todos os irmãos juntos em um único PDF
    — um requerimento por página — então um arquivo pode conter 1 ou
    vários alunos. detect_requerimento_blocks() identifica cada bloco
    (aluno) dentro do arquivo, e nome/segmento são extraídos individualmente
    por bloco, nunca uma única vez para o arquivo inteiro.
    """
    try:
        if 'files[]' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})

        files = request.files.getlist('files[]')

        if not files or files[0].filename == '':
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'})

        groups = []
        total_students = 0

        for file in files:
            if not (file and file.filename.lower().endswith('.pdf')):
                continue

            # Salvar arquivo temporariamente
            filename = sanitize_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            blocks = detect_requerimento_blocks(filepath)
            group_id = f"g{len(groups)}"
            group_students = []

            for idx, block in enumerate(blocks):
                student_name = extract_student_name_from_text(block['top_text'])
                if not student_name:
                    # Fallback: nome do arquivo (+ sufixo se houver mais de um aluno no arquivo)
                    base_name = sanitize_name_from_filename(filepath)
                    student_name = base_name if len(blocks) == 1 else f"{base_name} ({idx + 1})"

                contract_type = extract_course_segment(filepath, block['page_start'])
                print(f"[INFO] Aluno: {student_name} (págs {block['page_start']}-{block['page_end']}) -> Tipo de contrato: {contract_type}")

                group_students.append({
                    'id': f"{group_id}-{idx}",
                    'student_name': student_name,
                    'contract_type': contract_type,  # Detectado automaticamente (ou None p/ revisão manual)
                    'page_start': block['page_start'],
                    'page_end': block['page_end'],
                    'individual_filename': f"Contrato {student_name}_Colégio Anchieta.pdf"
                })

            if not group_students:
                continue

            names = [s['student_name'] for s in group_students]
            groups.append({
                'group_id': group_id,
                'original_filename': file.filename,
                'temp_filepath': filepath,
                'suggested_filename': f"Contrato{'s' if len(names) > 1 else ''} {format_names_list(names)}_Colégio Anchieta.pdf",
                # Mesclar por padrão quando há mais de um aluno no mesmo arquivo
                # (irmãos) — reflete o novo fluxo em que a secretaria já entrega
                # o bloco de irmãos junto. Pode ser desmarcado na revisão.
                'merge': len(group_students) > 1,
                'students': group_students
            })
            total_students += len(group_students)

        if not groups:
            return jsonify({'success': False, 'error': 'Nenhum PDF válido encontrado'})

        return jsonify({
            'success': True,
            'groups': groups,
            'total_groups': len(groups),
            'total_students': total_students
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/process', methods=['POST'])
def process_contracts():
    """
    Processa os contratos em lote com as configurações escolhidas.

    Recebe uma lista de "grupos" (um por arquivo/família enviado no
    upload). Cada grupo tem seus alunos (com página de origem e tipo de
    contrato já confirmados na revisão) e uma flag `merge`: quando True
    (padrão para famílias com mais de um filho), os requerimentos de todos
    os irmãos do grupo são concatenados com seus respectivos contratos em
    um único PDF final — permitindo inclusive tipos de contrato diferentes
    entre irmãos. Quando False, cada aluno do grupo vira um PDF separado.
    """
    try:
        data = request.json
        groups = data.get('groups', [])

        if not groups:
            return jsonify({'success': False, 'error': 'Nenhum grupo para processar'})

        # Nunca processar um aluno cujo tipo de contrato não foi confirmado
        # (nem pela detecção automática, nem manualmente pelo usuário).
        sem_tipo = [
            s.get('student_name', 'Desconhecido')
            for g in groups for s in g.get('students', [])
            if not s.get('contract_type')
        ]
        if sem_tipo:
            return jsonify({
                'success': False,
                'error': 'Selecione o tipo de contrato para: ' + ', '.join(sem_tipo)
            })

        results = []
        temp_files_used = set()

        for group in groups:
            temp_filepath = group.get('temp_filepath')
            students = group.get('students', [])
            if not students or not temp_filepath:
                continue
            temp_files_used.add(temp_filepath)

            merge = bool(group.get('merge')) and len(students) > 1

            if merge:
                names_str = format_names_list([s['student_name'] for s in students])
                final_filename = group.get('output_filename') or group.get('suggested_filename')
                try:
                    items = [{
                        'enrollment_path': temp_filepath,
                        'page_start': s['page_start'],
                        'page_end': s['page_end'],
                        'contract_type': s['contract_type']
                    } for s in students]

                    output_path = os.path.join(OUTPUT_FOLDER, final_filename)
                    build_pdf(items, output_path)

                    results.append({
                        'student_name': names_str,
                        'filename': final_filename,
                        'success': True,
                        'grouped': True
                    })
                except Exception as e:
                    results.append({
                        'student_name': names_str,
                        'filename': final_filename or '',
                        'success': False,
                        'error': str(e)
                    })
            else:
                for student in students:
                    final_filename = student.get('individual_filename')
                    try:
                        output_path = os.path.join(OUTPUT_FOLDER, final_filename)
                        build_pdf([{
                            'enrollment_path': temp_filepath,
                            'page_start': student['page_start'],
                            'page_end': student['page_end'],
                            'contract_type': student['contract_type']
                        }], output_path)

                        results.append({
                            'student_name': student['student_name'],
                            'filename': final_filename,
                            'success': True
                        })
                    except Exception as e:
                        results.append({
                            'student_name': student.get('student_name', 'Desconhecido'),
                            'filename': final_filename or '',
                            'success': False,
                            'error': str(e)
                        })

        # Remover arquivos temporários (uma vez por arquivo, após todos os
        # grupos que dependem dele terem sido processados)
        for temp_filepath in temp_files_used:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)

        successful = sum(1 for r in results if r['success'])

        return jsonify({
            'success': True,
            'results': results,
            'total': len(results),
            'successful': successful,
            'failed': len(results) - successful
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<filename>')
def download_file(filename):
    """
    Permite download do contrato processado.
    """
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'success': False, 'error': 'Arquivo não encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/clear-temp', methods=['POST'])
def clear_temp():
    """
    Limpa arquivos temporários da pasta de uploads.
    """
    try:
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        return jsonify({'success': True, 'message': 'Arquivos temporários removidos'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("=" * 60)
    print(" ContratIA v2.0 - Sistema de Processamento em Lote")
    print("=" * 60)
    print(f" Pasta de contratos base: {CONTRACTS_FOLDER}")
    print(f" Pasta de upload: {UPLOAD_FOLDER}")
    print(f" Pasta de saída: {OUTPUT_FOLDER}")
    print("=" * 60)
    print(" Servidor iniciado em: http://127.0.0.1:5000")
    print("=" * 60)
    
    app.run(debug=True, port=5000)