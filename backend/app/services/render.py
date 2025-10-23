

from docx import Document
import uuid
from pathlib import Path
from .services import _ensure_media_subdir
from docxtpl import DocxTemplate
import os 

# Renderização de DOCX via docxtpl a partir de um template base e contexto.
def render_docx_from_template(template_file_path: str, context: dict, dest_dir: str | None = None) -> str:
    """
    Gera um .docx preenchido a partir de um template .docx.
    Tenta primeiro docxtpl, depois renderização inteligente.
    Retorna o caminho absoluto do arquivo gerado.
    """
    if dest_dir is None:
        dest_dir = _ensure_media_subdir("documents", "docx")

    filename = f"{Path(template_file_path).stem}_{uuid.uuid4().hex[:8]}.docx"
    out_path = os.path.join(dest_dir, filename)

    # Verificar se o template tem tokens {{ }}
    has_tokens = False
    try:
        from docx import Document
        doc = Document(template_file_path)
        for p in doc.paragraphs[:20]:  # Verificar primeiros 20 parágrafos
            if '{{' in p.text and '}}' in p.text:
                has_tokens = True
                break
    except:
        pass
    
    if has_tokens:
        # Template tem tokens - usar docxtpl
        try:
            doc = DocxTemplate(template_file_path)
            doc.render(context)
            doc.save(out_path)
            print(f"✅ Renderização com docxtpl bem-sucedida")
            return out_path
        except Exception as e:
            print(f"⚠️ Docxtpl falhou: {e}")
            print("🔄 Tentando renderização inteligente...")
            render_docx_intelligent(template_file_path, out_path, context)
            print(f"✅ Renderização inteligente bem-sucedida")
            return out_path
    else:
        # Template não tem tokens - usar renderização contextual inteligente
        print("🔧 Template sem tokens - usando renderização contextual inteligente")
        user_prompt = context.get('user_prompt', '')
        render_docx_contextual_intelligent(template_file_path, out_path, context, user_prompt)
        print(f"✅ Renderização contextual inteligente bem-sucedida")
        return out_path

# Geração opcional de HTML de preview (pode ser usado com render_to_string em views).
def render_preview_html(template_obj, context: dict) -> str:
    """
    Retorna HTML de preview. Se o template_obj tiver preview_html (string),
    você pode renderizá-lo como um template Django (render_to_string) na view.
    Aqui assumimos que a view já chama render_to_string se quiser.
    """
    # pode implementar render_to_string('documents/preview_base.html', {...})
    return ""  # opcional, use render_to_string na view


# Renderização por estratégia "index": substitui conteúdo de parágrafos por índices de blocos.
def render_docx_by_index(template_path, out_path, mapping_schema, values: dict):
    """
    mapping_schema: TemplateSchema.schema
    values: dict {key: value}
    strategy index: for each field, replace text in block_indices with value
    """
    doc = Document(template_path)
    blocks = []  # map paragraph index -> paragraph object
    for i, p in enumerate(doc.paragraphs):
        blocks.append(p)

    # aplicar substituições
    for field in mapping_schema.get("fields", []):
        key = field["key"]
        indices = field.get("block_indices", [])
        val = values.get(key, "")
        for idx in indices:
            if idx < len(blocks):
                p = blocks[idx]
                # simplificar: limpar runs e inserir new text
                for r in list(p.runs):
                    p._p.remove(r._r)  # remove run (docx internals) - careful
                p.add_run(str(val))

    doc.save(out_path)
    return out_path

# Renderização por tokens: usa docxtpl com {{ chaves }} dentro do DOCX.
def render_docx_with_tokens(template_path: str, output_path: str, values: dict):
    """
    Gera um DOCX a partir de um template com marcações {{ }} via docxtpl.
    """
    tpl = DocxTemplate(template_path)
    tpl.render(values)
    tpl.save(output_path)
    return output_path

# Renderização contextual inteligente: analisa o documento e aplica mudanças baseadas no contexto
def render_docx_contextual_intelligent(template_path: str, output_path: str, values: dict, user_prompt: str = ""):
    """
    Renderização contextual inteligente que analisa o documento e aplica mudanças
    baseadas no contexto e no prompt do usuário, sem depender de tokens {{ }}.
    """
    from docx import Document
    import re
    
    doc = Document(template_path)
    
    print(f"🧠 Renderização contextual inteligente")
    print(f"📝 Prompt do usuário: {user_prompt[:100]}...")
    print(f"📊 Dados disponíveis: {list(values.keys())}")
    
    # Mapear campos para valores
    field_map = {}
    for key, value in values.items():
        if value is not None:
            # Não converter listas e dicionários para string
            if isinstance(value, (list, dict)):
                field_map[key] = value
            else:
                field_map[key] = str(value)
    
    # Análise contextual do documento
    context_analysis = analyze_document_context(doc, user_prompt)
    print(f"🔍 Análise contextual: {context_analysis}")
    
    # Aplicar mudanças baseadas no contexto
    changes_applied = 0
    
    # 1. Aplicar mudanças em parágrafos
    for p in doc.paragraphs:
        original_text = p.text
        new_text = apply_contextual_changes(original_text, field_map, context_analysis, user_prompt)
        
        if new_text != original_text:
            changes_applied += 1
            print(f"  🔄 Mudança {changes_applied}: {original_text[:60]}... -> {new_text[:60]}...")
            
            # Limpar runs e adicionar novo texto
            for r in list(p.runs):
                p._p.remove(r._r)
            p.add_run(new_text)
    
    # 2. Aplicar mudanças em tabelas
    for table_idx, table in enumerate(doc.tables):
        for row_idx, row in enumerate(table.rows):
            for cell_idx, cell in enumerate(row.cells):
                for p in cell.paragraphs:
                    original_text = p.text
                    new_text = apply_contextual_changes(original_text, field_map, context_analysis, user_prompt)
                    
                    if new_text != original_text:
                        changes_applied += 1
                        print(f"  🔄 Mudança {changes_applied} (Tabela {table_idx}, Linha {row_idx}, Célula {cell_idx}): {original_text[:60]}... -> {new_text[:60]}...")
                        
                        # Limpar runs e adicionar novo texto
                        for r in list(p.runs):
                            p._p.remove(r._r)
                        p.add_run(new_text)
    
    # 3. Adicionar conteúdo de especialista baseado no prompt e dados estruturados
    if 'especialista' in user_prompt.lower() or 'licitações' in user_prompt.lower():
        changes_applied += add_expert_content(doc, user_prompt, field_map)
    
    print(f"✅ Total de mudanças aplicadas: {changes_applied}")
    doc.save(output_path)
    return output_path

def add_expert_content(doc, user_prompt, field_map=None):
    """Analisa o prompt do usuário e aplica mudanças inteligentes no documento."""
    from docx.shared import RGBColor
    from docx.oxml.shared import OxmlElement, qn
    import re
    
    changes_applied = 0
    
    print("🧠 Analisando prompt para mudanças inteligentes...")
    
    # Usar dados estruturados se disponíveis
    if field_map is None:
        field_map = {}
    
    # 1. Análise inteligente de valores monetários
    valor_matches = re.findall(r'R\$\s*([\d.,]+)', user_prompt)
    if valor_matches:
        print(f"  💰 Valores detectados no prompt: {valor_matches}")
        for valor in valor_matches:
            novo_valor = f"R$ {valor}"
            # Procurar e substituir valores em tabelas
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                if "R$" in run.text and any(char.isdigit() for char in run.text):
                                    old_text = run.text
                                    run.text = novo_valor
                                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                    print(f"  ✅ Valor alterado: {old_text} -> {novo_valor}")
                                    changes_applied += 1
            
            # Procurar em parágrafos também (para templates simples)
            for paragraph in doc.paragraphs:
                for run in paragraph.runs:
                    if "R$" in run.text and any(char.isdigit() for char in run.text):
                        old_text = run.text
                        run.text = novo_valor
                        run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                        print(f"  ✅ Valor alterado (parágrafo): {old_text} -> {novo_valor}")
                        changes_applied += 1
    
    # 2. Análise inteligente de nomes e locais
    nome_matches = re.findall(r'(?:mude|altere|troque|substitua).*?(?:para|por)\s+([A-ZÁÊÇÕ][a-záêçõ\s]+)', user_prompt, re.IGNORECASE)
    if nome_matches:
        print(f"  🏛️ Nomes/locais detectados no prompt: {nome_matches}")
        for nome in nome_matches:
            nome = nome.strip()
            # Procurar e substituir nomes em todo o documento
            for paragraph in doc.paragraphs:
                for run in paragraph.runs:
                    if any(palavra in run.text for palavra in ['ITAJÁ', 'GOIÂNIA', 'MUNICÍPIO', 'PREFEITURA']):
                        old_text = run.text
                        # Substituir baseado no contexto
                        if 'ITAJÁ' in old_text and 'GOIÂNIA' in nome.upper():
                            run.text = old_text.replace('ITAJÁ', nome.upper())
                            run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                            print(f"  ✅ Nome alterado: {old_text} -> {run.text}")
                            changes_applied += 1
    
    # 3. Análise inteligente de números e datas
    numero_matches = re.findall(r'(?:número|edital|processo)\s*(\d+/\d+)', user_prompt, re.IGNORECASE)
    if numero_matches:
        print(f"  📋 Números detectados no prompt: {numero_matches}")
        for numero in numero_matches:
            # Procurar e substituir números de edital
            for paragraph in doc.paragraphs:
                for run in paragraph.runs:
                    if re.search(r'\d+/\d+', run.text):
                        old_text = run.text
                        run.text = re.sub(r'\d+/\d+', numero, old_text)
                        run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                        print(f"  ✅ Número alterado: {old_text} -> {run.text}")
                        changes_applied += 1
    
    # 4. Substituições específicas para campos do template
    print("  🔧 Aplicando substituições específicas do template...")
    
    # Substituir campos específicos do template
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            original_text = run.text
            
            # Substituir PROCESSO Nº
            if "PROCESSO Nº: ____________" in original_text:
                if 'numero_edital' in field_map:
                    run.text = original_text.replace("____________", field_map['numero_edital'])
                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                    print(f"  ✅ Processo alterado: {field_map['numero_edital']}")
                    changes_applied += 1
            
            # Substituir MODALIDADE
            if "MODALIDADE: ____________" in original_text:
                if 'modalidade' in field_map:
                    run.text = original_text.replace("____________", field_map['modalidade'])
                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                    print(f"  ✅ Modalidade alterada: {field_map['modalidade']}")
                    changes_applied += 1
            
            # Substituir DATA DE ABERTURA
            if "DATA DE ABERTURA: ____/____/______" in original_text:
                if 'data_abertura' in field_map:
                    run.text = original_text.replace("____/____/______", field_map['data_abertura'])
                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                    print(f"  ✅ Data alterada: {field_map['data_abertura']}")
                    changes_applied += 1
            
            # Substituir LOCAL
            if "LOCAL: ____________________________" in original_text:
                if 'local_orgao' in field_map:
                    run.text = original_text.replace("____________________________", field_map['local_orgao'])
                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                    print(f"  ✅ Local alterado: {field_map['local_orgao']}")
                    changes_applied += 1
            
            # Substituir OBJETO
            if "contratação de ____________" in original_text:
                if 'objeto' in field_map:
                    run.text = original_text.replace("____________", field_map['objeto'])
                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                    print(f"  ✅ Objeto alterado: {field_map['objeto']}")
                    changes_applied += 1
    
    # 3.1. Substituições contextuais inteligentes (MELHORADO)
    changes_applied += apply_contextual_intelligent_replacements(doc, field_map, user_prompt)
    
    # 4. Análise inteligente de conteúdo a ser adicionado
    # Usar dados estruturados primeiro, depois fallback para análise do prompt
    adicionar_clausula = field_map.get('adicionar_clausula_julgamento', False) if field_map else False
    adicionar_observacao = field_map.get('adicionar_observacao_pratica', False) if field_map else False
    clausulas_especificas = field_map.get('clausulas_especificas', []) if field_map else []
    
    # Garantir que clausulas_especificas é uma lista
    if not isinstance(clausulas_especificas, list):
        print(f"  ⚠️ clausulas_especificas não é uma lista: {type(clausulas_especificas)}")
        clausulas_especificas = []
    
    # Fallback para análise do prompt se dados estruturados não estiverem disponíveis
    if not adicionar_clausula and ("adicionar" in user_prompt.lower() or "incluir" in user_prompt.lower()):
        adicionar_clausula = "julgamento" in user_prompt.lower() and ("técnica" in user_prompt.lower() or "preço" in user_prompt.lower())
    
    if not adicionar_observacao and ("adicionar" in user_prompt.lower() or "incluir" in user_prompt.lower()):
        adicionar_observacao = "observação" in user_prompt.lower() and "prática" in user_prompt.lower()
    
    if adicionar_clausula or adicionar_observacao or clausulas_especificas:
        print("  📝 Analisando conteúdo para adicionar...")
        
        # Adicionar cláusulas específicas solicitadas
        if clausulas_especificas:
            print(f"  📋 Processando {len(clausulas_especificas)} cláusula(s) específica(s)...")
            for clausula_info in clausulas_especificas:
                try:
                    from backend.app.services.ia import gerar_clausula_especifica
                    
                    # Verificar se clausula_info é um dicionário
                    if not isinstance(clausula_info, dict):
                        print(f"  ❌ Cláusula não é um dicionário: {type(clausula_info)}")
                        continue
                    
                    clausula = gerar_clausula_especifica(
                        clausula_info.get('tipo', 'clausula'), 
                        clausula_info.get('descricao', '')
                    )
                    
                    print(f"  ⚖️ Adicionando cláusula: {clausula_info.get('descricao', 'N/A')}")
                    
                    # Encontrar local apropriado para adicionar a cláusula (sequência 3.4.x)
                    # Estratégia: encontrar a seção 3.4.x e inserir na sequência correta
                    
                    # 1. Encontrar todos os parágrafos com numeração 3.4.x (não 13.4.x)
                    clausulas_3_4 = []
                    for i, p in enumerate(doc.paragraphs):
                        # Regex mais específico: deve começar com 3.4. e não ser precedido por dígito
                        match = re.search(r'(?<!\d)3\.4\.(\d+)', p.text)
                        if match:
                            clausulas_3_4.append({
                                'indice': i,
                                'numero': int(match.group(1)),
                                'paragrafo': p,
                                'texto': p.text.strip()
                            })
                    
                    # 2. Ordenar por número para manter sequência
                    clausulas_3_4.sort(key=lambda x: x['numero'])
                    
                    if clausulas_3_4:
                        print(f"  📍 Encontrado {len(clausulas_3_4)} cláusulas 3.4.x existentes")
                        
                        # 3. Encontrar o próximo número disponível
                        numeros_existentes = [c['numero'] for c in clausulas_3_4]
                        proximo_numero = max(numeros_existentes) + 1
                        
                        # 4. Atualizar o texto da cláusula com o número correto
                        clausula_texto_atualizado = clausula['texto']
                        # Substituir o número da cláusula pelo próximo disponível
                        clausula_texto_atualizado = re.sub(r'3\.4\.\d+', f'3.4.{proximo_numero}', clausula_texto_atualizado)
                        
                        # 5. Encontrar o local correto para inserir (após a última cláusula 3.4.x)
                        ultima_clausula = clausulas_3_4[-1]
                        print(f"  📍 Inserindo cláusula 3.4.{proximo_numero} após 3.4.{ultima_clausula['numero']}")
                        
                        # 6. Inserir após a última cláusula 3.4.x
                        new_p_elem = OxmlElement('w:p')
                        ultima_clausula['paragrafo']._element.addnext(new_p_elem)
                        new_p = type(ultima_clausula['paragrafo'])(new_p_elem, ultima_clausula['paragrafo']._parent)
                        
                        run = new_p.add_run()
                        run.text = clausula_texto_atualizado
                        run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                        print(f"  ✅ Adicionada cláusula específica 3.4.{proximo_numero}: {clausula_info.get('descricao', 'N/A')}")
                        changes_applied += 1
                        
                    else:
                        # Fallback: procurar por seção de julgamento ou qualquer seção numerada
                        print("  🔍 Procurando seção apropriada (fallback)...")
                        
                        # Primeiro, tentar encontrar seção de julgamento
                        for i, p in enumerate(doc.paragraphs):
                            texto = p.text.strip()
                            if ('julgamento' in texto.lower() and 
                                ('proposta' in texto.lower() or 'critério' in texto.lower())):
                                
                                print(f"  📍 Encontrado parágrafo de julgamento: {i+1}")
                                
                                # Adicionar cláusula específica
                                new_p_elem = OxmlElement('w:p')
                                p._element.addnext(new_p_elem)
                                new_p = type(p)(new_p_elem, p._parent)
                                
                                run = new_p.add_run()
                                run.text = clausula['texto']
                                run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                print(f"  ✅ Adicionada cláusula específica após julgamento: {clausula_info.get('descricao', 'N/A')}")
                                changes_applied += 1
                                break
                        else:
                            # Se não encontrar julgamento, procurar por qualquer seção numerada
                            print("  🔍 Procurando qualquer seção numerada...")
                            
                            for i, p in enumerate(doc.paragraphs):
                                texto = p.text.strip()
                                # Procurar por seções numeradas (1., 2., 3., etc.)
                                if re.search(r'^\d+\.\s+[A-Z]', texto):
                                    print(f"  📍 Encontrado parágrafo numerado: {i+1} - {texto[:50]}...")
                                    
                                    # Adicionar cláusula específica
                                    new_p_elem = OxmlElement('w:p')
                                    p._element.addnext(new_p_elem)
                                    new_p = type(p)(new_p_elem, p._parent)
                                    
                                    run = new_p.add_run()
                                    run.text = clausula['texto']
                                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                    print(f"  ✅ Adicionada cláusula específica após seção: {clausula_info.get('descricao', 'N/A')}")
                                    changes_applied += 1
                                    break
                            else:
                                # Último fallback: adicionar no final do documento
                                print("  🔍 Adicionando no final do documento (último fallback)...")
                                
                                # Encontrar o último parágrafo com conteúdo
                                ultimo_paragrafo = None
                                for i, p in enumerate(doc.paragraphs):
                                    if p.text.strip():
                                        ultimo_paragrafo = p
                                
                                if ultimo_paragrafo:
                                    new_p_elem = OxmlElement('w:p')
                                    ultimo_paragrafo._element.addnext(new_p_elem)
                                    new_p = type(ultimo_paragrafo)(new_p_elem, ultimo_paragrafo._parent)
                                    
                                    run = new_p.add_run()
                                    run.text = clausula['texto']
                                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                    print(f"  ✅ Adicionada cláusula específica no final: {clausula_info.get('descricao', 'N/A')}")
                                    changes_applied += 1
                                else:
                                    print("  ⚠️ Não foi possível encontrar local apropriado para inserir cláusula")
                except Exception as e:
                    print(f"  ❌ Erro ao processar cláusula: {e}")
                    continue
        
        # Adicionar cláusula de julgamento (apenas se não foi adicionada como cláusula específica)
        if adicionar_clausula and not clausulas_especificas:
            print("  ⚖️ Adicionando cláusula de julgamento")
            
            # Encontrar seção 3.4.x para inserir (não 13.4.x)
            clausulas_3_4 = []
            for i, p in enumerate(doc.paragraphs):
                # Regex mais específico: deve começar com 3.4. e não ser precedido por dígito
                match = re.search(r'(?<!\d)3\.4\.(\d+)', p.text)
                if match:
                    clausulas_3_4.append({
                        'indice': i,
                        'numero': int(match.group(1)),
                        'paragrafo': p
                    })
            
            if clausulas_3_4:
                # Ordenar por número e usar a última cláusula 3.4.x
                clausulas_3_4.sort(key=lambda x: x['numero'])
                ultima_clausula = clausulas_3_4[-1]
                
                print(f"  📍 Inserindo cláusula de julgamento após 3.4.{ultima_clausula['numero']}")
                
                new_p_elem = OxmlElement('w:p')
                ultima_clausula['paragrafo']._element.addnext(new_p_elem)
                new_p = type(ultima_clausula['paragrafo'])(new_p_elem, ultima_clausula['paragrafo']._parent)
                
                run = new_p.add_run()
                run.text = "3.4.15. O julgamento das propostas será realizado mediante análise técnica e de preço, conforme disposto no art. 46 da Lei 14.133/2021, considerando os critérios de aceitabilidade e economicidade."
                run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                print(f"  ✅ Adicionada cláusula de julgamento na seção 3.4.x")
                changes_applied += 1
            else:
                print("  ⚠️ Não foi possível encontrar seção 3.4.x para inserir cláusula de julgamento")
        
        # Adicionar observação prática
        if adicionar_observacao:
            print("  📝 Adicionando observação prática")
            for i, p in enumerate(doc.paragraphs):
                if "15.16" in p.text or "julgamento" in p.text.lower():
                    print(f"  📍 Encontrado parágrafo para observação: {i+1}")
                    new_p_elem = OxmlElement('w:p')
                    p._element.addnext(new_p_elem)
                    new_p = type(p)(new_p_elem, p._parent)
                    
                    run = new_p.add_run()
                    run.text = "OBSERVAÇÃO PRÁTICA: Recomenda-se que o pregoeiro mantenha registro detalhado de todas as etapas do processo, incluindo justificativas para aceitação ou rejeição de propostas, conforme orientação do TCU."
                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                    print(f"  ✅ Adicionada observação prática após parágrafo {i+1}")
                    changes_applied += 1
                    break
    
    print(f"  📊 Total de mudanças de especialista: {changes_applied}")
    return changes_applied

def analyze_document_context(doc, user_prompt):
    """Analisa o contexto do documento para identificar padrões de substituição."""
    import re
    
    context = {
        'municipio': None,
        'estado': None,
        'numero_edital': None,
        'numero_pregao': None,
        'objeto': None,
        'modalidade': None,
        'valor': None,
        'data': None
    }
    
    # Procurar padrões no documento
    for p in doc.paragraphs:
        text = p.text
        
        # Identificar município e estado
        if 'MUNICÍPIO DE' in text:
            match = re.search(r'MUNICÍPIO DE ([^/]+)/([A-Z]{2})', text)
            if match:
                context['municipio'] = match.group(1).strip()
                context['estado'] = match.group(2).strip()
        
        # Identificar número do edital
        if 'EDITAL N.' in text or 'EDITAL Nº' in text:
            match = re.search(r'EDITAL N[.º]\s*(\d+/\d{4})', text)
            if match:
                context['numero_edital'] = match.group(1)
        
        # Identificar número do pregão
        if 'PREGÃO' in text and 'N.' in text:
            match = re.search(r'PREGÃO[^N]*N[.º]\s*(\d+/\d{4})', text)
            if match:
                context['numero_pregao'] = match.group(1)
        
        # Identificar objeto
        if 'Aquisição de' in text or 'Contratação de' in text:
            context['objeto'] = text.strip()
        
        # Identificar modalidade
        if 'PREGÃO ELETRÔNICO' in text:
            context['modalidade'] = 'PREGÃO ELETRÔNICO'
    
    return context

def apply_contextual_changes(text, field_map, context_analysis, user_prompt):
    """Aplica mudanças contextuais no texto baseado no prompt e dados estruturados."""
    import re
    new_text = text
    
    # 1. Substituições específicas baseadas nos dados estruturados extraídos
    
    # Número do edital
    if 'numero_edital' in field_map and field_map['numero_edital']:
        # Substituir qualquer número de edital existente
        edital_pattern = r'EDITAL\s*N[.º]?\s*\d+/\d+'
        if re.search(edital_pattern, new_text):
            new_text = re.sub(edital_pattern, f"EDITAL N. {field_map['numero_edital']}", new_text)
        # Também substituir em outros contextos
        edital_simple_pattern = r'\d+/\d+'
        if re.search(edital_simple_pattern, new_text) and 'EDITAL' in new_text:
            new_text = re.sub(edital_simple_pattern, field_map['numero_edital'], new_text, count=1)
    
    # Data de abertura
    if 'data_abertura' in field_map and field_map['data_abertura']:
        data_pattern = r'\d{1,2}/\d{1,2}/\d{4}'
        if re.search(data_pattern, new_text):
            new_text = re.sub(data_pattern, field_map['data_abertura'], new_text)
    
    # Local/Órgão - BRASÍLIA
    if 'local_orgao' in field_map and field_map['local_orgao'] == 'BRASÍLIA':
        # Substituir ITAJÁ por BRASÍLIA
        if 'ITAJÁ' in new_text:
            new_text = new_text.replace('ITAJÁ', 'BRASÍLIA')
        if 'Itajá' in new_text:
            new_text = new_text.replace('Itajá', 'Brasília')
        if 'itajá' in new_text:
            new_text = new_text.replace('itajá', 'brasília')
    
    # Órgão específico
    if 'orgao' in field_map and 'SECRETARIA' in field_map['orgao'].upper():
        # Substituir referências genéricas por órgão específico
        if 'Prefeitura Municipal' in new_text:
            new_text = new_text.replace('Prefeitura Municipal', field_map['orgao'])
        if 'MUNICÍPIO' in new_text and 'ITAJÁ' in new_text:
            new_text = new_text.replace('MUNICÍPIO DE ITAJÁ/GO', f"MUNICÍPIO DE BRASÍLIA/DF - {field_map['orgao']}")
    
    # Valor estimado
    if 'valor_estimado' in field_map and field_map['valor_estimado']:
        valor = field_map['valor_estimado']
        try:
            valor_float = float(valor)
            valor_formatado = f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            # Procurar e substituir valores monetários
            valor_pattern = r'R\$\s*[\d.,]+'
            if re.search(valor_pattern, new_text):
                new_text = re.sub(valor_pattern, valor_formatado, new_text)
            
            # Também substituir valores sem R$
            valor_simples_pattern = r'\d{1,3}(?:\.\d{3})*(?:,\d{2})?'
            if re.search(valor_simples_pattern, new_text) and 'R$' in new_text:
                new_text = re.sub(valor_simples_pattern, valor_formatado.replace('R$ ', ''), new_text)
        except:
            pass
    
    # Prazo de execução
    if 'prazo_execucao' in field_map and field_map['prazo_execucao']:
        prazo_pattern = r'\d+\s*dias?'
        if re.search(prazo_pattern, new_text, re.IGNORECASE):
            new_text = re.sub(prazo_pattern, f"{field_map['prazo_execucao']} dias", new_text, flags=re.IGNORECASE)
    
    # 2. Substituições baseadas no prompt do usuário (fallback)
    if 'goiânia' in user_prompt.lower() or 'goiania' in user_prompt.lower():
        # Substituir município para Goiânia
        if context_analysis['municipio'] and context_analysis['estado']:
            old_municipio = f"MUNICÍPIO DE {context_analysis['municipio']}/{context_analysis['estado']}"
            new_municipio = "MUNICÍPIO DE GOIÂNIA/GO"
            new_text = new_text.replace(old_municipio, new_municipio)
            
            # Substituir referências ao município
            new_text = new_text.replace(context_analysis['municipio'], 'GOIÂNIA')
            new_text = new_text.replace(context_analysis['municipio'].lower(), 'Goiânia')
    
    # 3. Substituições genéricas baseadas no contexto
    if 'numero_edital' in field_map and context_analysis['numero_edital']:
        new_text = new_text.replace(context_analysis['numero_edital'], field_map['numero_edital'])
    
    if 'numero_pregao' in field_map and context_analysis['numero_pregao']:
        new_text = new_text.replace(context_analysis['numero_pregao'], field_map['numero_pregao'])
    
    if 'modalidade' in field_map and context_analysis['modalidade']:
        new_text = new_text.replace(context_analysis['modalidade'], field_map['modalidade'])
    
    if 'objeto' in field_map and context_analysis['objeto']:
        # Substituir objeto de forma mais inteligente
        if 'Aquisição de Medicamentos' in new_text:
            new_text = new_text.replace('Aquisição de Medicamentos', field_map['objeto'])
    
    # 4. Aplicar formatação em azul se solicitado
    if 'azul' in user_prompt.lower() or 'blue' in user_prompt.lower():
        # Marcar texto para formatação em azul (será aplicado na renderização)
        if new_text != text:  # Se houve mudança
            new_text = f"[AZUL]{new_text}[/AZUL]"
    
    return new_text

# Renderização inteligente: substitui texto baseado em padrões específicos
def render_docx_intelligent(template_path: str, output_path: str, values: dict):
    """
    Renderização inteligente que substitui texto baseado em padrões específicos.
    Funciona com templates que não têm tokens {{ }}.
    """
    from docx import Document
    import re
    
    doc = Document(template_path)
    
    # Mapear campos para valores
    field_map = {}
    for key, value in values.items():
        if value is not None:
            field_map[key] = str(value)
    
    print(f"🔧 Renderização inteligente - Mapeamento: {field_map}")
    
    # Substituir em todos os parágrafos
    for p in doc.paragraphs:
        original_text = p.text
        new_text = original_text
        
        # Padrões de substituição baseados no conteúdo
        if "N. 014/2025" in original_text or "N.º 014/2025" in original_text:
            new_text = original_text.replace("014/2025", field_map.get('numero_edital', '014/2025'))
        elif "N. 005/2025" in original_text or "N.º 005/2025" in original_text:
            new_text = original_text.replace("005/2025", field_map.get('numero_pregao', '005/2025'))
        elif "PREGÃO ELETRÔNICO" in original_text:
            new_text = original_text.replace("PREGÃO ELETRÔNICO", field_map.get('modalidade', 'PREGÃO ELETRÔNICO'))
        elif "Aquisição de Medicamentos" in original_text:
            new_text = original_text.replace("Aquisição de Medicamentos", field_map.get('objeto', 'Aquisição de Medicamentos'))
        elif "MUNICÍPIO DE ITAJÁ/GO" in original_text:
            new_text = original_text.replace("MUNICÍPIO DE ITAJÁ/GO", field_map.get('orgao', 'MUNICÍPIO DE ITAJÁ/GO'))
        elif "Lei Federal nº 14.133/2021" in original_text:
            new_text = original_text.replace("Lei Federal nº 14.133/2021", field_map.get('base_legal', 'Lei Federal nº 14.133/2021'))
        
        # Substituições mais genéricas
        if "R$ 150.000,00" in original_text:
            new_text = original_text.replace("R$ 150.000,00", field_map.get('valor_estimado', 'R$ 150.000,00'))
        if "90 dias" in original_text:
            new_text = original_text.replace("90 dias", field_map.get('prazo_execucao', '90 dias'))
        if "15/03/2025" in original_text:
            new_text = original_text.replace("15/03/2025", field_map.get('data_abertura', '15/03/2025'))
        
        if new_text != original_text:
            print(f"  🔄 Substituído: {original_text[:50]}... -> {new_text[:50]}...")
            # Limpar runs e adicionar novo texto
            for r in list(p.runs):
                p._p.remove(r._r)
            p.add_run(new_text)
    
    doc.save(output_path)
    return output_path

def apply_contextual_intelligent_replacements(doc, field_map, user_prompt):
    """
    Aplica substituições contextuais inteligentes, preservando referências legais
    e fazendo alterações apenas no contexto apropriado.
    """
    from docx.shared import RGBColor
    import re
    
    changes_applied = 0
    
    print("  🧠 Aplicando substituições contextuais inteligentes...")
    
    # Padrões que devem ser preservados (referências legais)
    LEGAL_PATTERNS = [
        r'Lei\s+\d+\.\d+/\d+',           # Lei 14.133/2021
        r'Lei\s+n\.\d+',                 # Lei n.º 14.133
        r'Lei\s+nº\s+\d+',               # Lei nº 14.133
        r'Decreto\s+\d+\.\d+/\d+',       # Decreto 10.024/19
        r'Decreto\s+Federal\s+\d+\.\d+/\d+', # Decreto Federal 10.024/19
        r'Lei\s+Complementar\s+\d+/\d+', # Lei Complementar 123/2006
        r'Lei\s+Complementar\s+nº\s+\d+/\d+', # Lei Complementar nº 123/2006
        r'art\.\s+\d+',                  # art. 156
        r'artigo\s+\d+',                 # artigo 156
        r'§\d+',                         # §5º
        r'parágrafo\s+\d+',              # parágrafo 1º
        r'parágrafo\s+\d+º',             # parágrafo 1º
        r'inciso\s+[IVX]+',              # inciso I, IV
        r'inciso\s+\d+',                 # inciso 1, 2
        # Padrões mais específicos para evitar falsos positivos
        r'Lei\s+Federal\s+nº\s+\d+\.\d+/\d+', # Lei Federal nº 14.133/2021
        r'Lei\s+Complementar\s+n\.\d+',  # Lei Complementar n.º 123
        r'Decreto\s+n\.\d+',             # Decreto n.º 10.024
        r'Decreto\s+nº\s+\d+',           # Decreto nº 10.024
    ]
    
    def is_legal_reference(text):
        """Verifica se o texto contém referências legais que devem ser preservadas"""
        # Verificar padrões específicos de referências legais
        legal_indicators = [
            'Lei', 'Decreto', 'art.', 'artigo', '§', 'parágrafo', 'inciso',
            'Lei Federal', 'Lei Complementar', 'Decreto Federal'
        ]
        
        # Se contém indicadores legais, verificar se é realmente uma referência
        has_legal_indicator = any(indicator in text for indicator in legal_indicators)
        if not has_legal_indicator:
            return False
        
        # Verificar padrões específicos
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in LEGAL_PATTERNS)
    
    def should_replace_in_context(text, replacement_type):
        """Verifica se deve fazer substituição baseado no contexto"""
        if is_legal_reference(text):
            return False
        
        if replacement_type == 'edital':
            # Verificar se é realmente um número de edital, não uma referência legal
            edital_indicators = ['EDITAL', 'edital', 'PREGÃO', 'pregão', 'SRP']
            has_edital_indicator = any(indicator in text.upper() for indicator in edital_indicators)
            has_number_pattern = bool(re.search(r'\d+/\d+', text))
            
            # Não substituir se contém referências legais
            legal_indicators = ['Lei', 'Decreto', 'art.', 'artigo', '§', 'parágrafo', 'inciso']
            has_legal_indicator = any(indicator in text for indicator in legal_indicators)
            
            return has_edital_indicator and has_number_pattern and not has_legal_indicator
            
        elif replacement_type == 'data':
            return any(word in text.lower() for word in ['abertura', 'sessão', 'julgamento', 'dia'])
        elif replacement_type == 'valor':
            return 'R$' in text or 'valor' in text.lower()
        elif replacement_type == 'local':
            return any(word in text.upper() for word in ['MUNICÍPIO', 'PREFEITURA', 'ITAJÁ', 'BRASÍLIA'])
        
        return False
    
    # 1. Substituições de números de edital (contextual)
    if 'numero_edital' in field_map and field_map['numero_edital']:
        numero_edital = field_map['numero_edital']
        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                if should_replace_in_context(run.text, 'edital') and re.search(r'\d+/\d+', run.text):
                    old_text = run.text
                    # Substituir apenas números de edital, não referências legais
                    if 'EDITAL' in old_text.upper() and not is_legal_reference(old_text):
                        # Padrões específicos para números de edital
                        patterns = [
                            r'EDITAL\s*N[.º]?\s*\d+/\d+',
                            r'Edital\s*N[.º]?\s*\d+/\d+',
                            r'edital\s*N[.º]?\s*\d+/\d+',
                            r'PREGÃO\s*ELETRÔNICO\s*SRP\s*N[.º]?\s*\d+/\d+',
                            r'Pregão\s*Eletrônico\s*SRP\s*N[.º]?\s*\d+/\d+',
                        ]
                        
                        new_text = old_text
                        for pattern in patterns:
                            if re.search(pattern, new_text, re.IGNORECASE):
                                new_text = re.sub(pattern, f'EDITAL N. {numero_edital}', new_text, flags=re.IGNORECASE)
                                break
                        
                        if new_text != old_text:
                            run.text = new_text
                            run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                            print(f"  ✅ Edital alterado: {old_text} -> {new_text}")
                            changes_applied += 1
    
    # 2. Substituições de data (contextual)
    if 'data_abertura' in field_map and field_map['data_abertura']:
        data_abertura = field_map['data_abertura']
        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                if should_replace_in_context(run.text, 'data') and re.search(r'\d{1,2}/\d{1,2}/\d{4}', run.text):
                    old_text = run.text
                    # Substituir apenas datas de abertura/sessão, não referências legais
                    if any(word in old_text.lower() for word in ['abertura', 'sessão', 'julgamento']):
                        new_text = re.sub(r'\d{1,2}/\d{1,2}/\d{4}', data_abertura, old_text)
                        if new_text != old_text:
                            run.text = new_text
                            run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                            print(f"  ✅ Data alterada: {old_text} -> {new_text}")
                            changes_applied += 1
    
    # 3. Substituições de valor (contextual)
    if 'valor_estimado' in field_map and field_map['valor_estimado']:
        valor = field_map['valor_estimado']
        try:
            valor_float = float(valor)
            valor_formatado = f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except:
            valor_formatado = f"R$ {valor}"
        
        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                if should_replace_in_context(run.text, 'valor') and 'R$' in run.text:
                    old_text = run.text
                    new_text = re.sub(r'R\$\s*[\d.,]+', valor_formatado, old_text)
                    if new_text != old_text:
                        run.text = new_text
                        run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                        print(f"  ✅ Valor alterado: {old_text} -> {new_text}")
                        changes_applied += 1
    
    # 4. Substituições de local (contextual)
    if 'local_orgao' in field_map and field_map['local_orgao'] == 'BRASÍLIA':
        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                if should_replace_in_context(run.text, 'local') and 'ITAJÁ' in run.text:
                    old_text = run.text
                    new_text = old_text.replace('ITAJÁ', 'BRASÍLIA')
                    if new_text != old_text:
                        run.text = new_text
                        run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                        print(f"  ✅ Local alterado: {old_text} -> {new_text}")
                        changes_applied += 1
    
    # 5. Substituições em tabelas (contextual)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        # Aplicar as mesmas regras contextuais nas tabelas
                        if should_replace_in_context(run.text, 'edital') and re.search(r'\d+/\d+', run.text):
                            old_text = run.text
                            if 'EDITAL' in old_text.upper() and not is_legal_reference(old_text):
                                # Padrões específicos para números de edital em tabelas
                                patterns = [
                                    r'EDITAL\s*N[.º]?\s*\d+/\d+',
                                    r'Edital\s*N[.º]?\s*\d+/\d+',
                                    r'edital\s*N[.º]?\s*\d+/\d+',
                                    r'PREGÃO\s*ELETRÔNICO\s*SRP\s*N[.º]?\s*\d+/\d+',
                                    r'Pregão\s*Eletrônico\s*SRP\s*N[.º]?\s*\d+/\d+',
                                ]
                                
                                new_text = old_text
                                for pattern in patterns:
                                    if re.search(pattern, new_text, re.IGNORECASE):
                                        new_text = re.sub(pattern, f'EDITAL N. {field_map.get("numero_edital", "")}', new_text, flags=re.IGNORECASE)
                                        break
                                
                                if new_text != old_text:
                                    run.text = new_text
                                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                    print(f"  ✅ Edital (tabela) alterado: {old_text} -> {new_text}")
                                    changes_applied += 1
                        
                        if should_replace_in_context(run.text, 'data') and re.search(r'\d{1,2}/\d{1,2}/\d{4}', run.text):
                            old_text = run.text
                            if any(word in old_text.lower() for word in ['abertura', 'sessão', 'julgamento']):
                                new_text = re.sub(r'\d{1,2}/\d{1,2}/\d{4}', field_map.get("data_abertura", ""), old_text)
                                if new_text != old_text:
                                    run.text = new_text
                                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                    print(f"  ✅ Data (tabela) alterada: {old_text} -> {new_text}")
                                    changes_applied += 1
                        
                        if should_replace_in_context(run.text, 'valor') and 'R$' in run.text:
                            old_text = run.text
                            valor = field_map.get('valor_estimado', '')
                            if valor:
                                try:
                                    valor_float = float(valor)
                                    valor_formatado = f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                                except:
                                    valor_formatado = f"R$ {valor}"
                                new_text = re.sub(r'R\$\s*[\d.,]+', valor_formatado, old_text)
                                if new_text != old_text:
                                    run.text = new_text
                                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                    print(f"  ✅ Valor (tabela) alterado: {old_text} -> {new_text}")
                                    changes_applied += 1
    
    print(f"  📊 Substituições contextuais aplicadas: {changes_applied}")
    return changes_applied
