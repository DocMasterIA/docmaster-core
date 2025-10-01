# MDLicitatech

MDLicitatech é uma aplicação web em **Django** para auxiliar servidores públicos e empresas na elaboração de documentos de licitação, trazendo agilidade, padronização e transparência.

O projeto nasceu para digitalizar processos antes feitos manualmente (ex.: termos de referência, ETP, DFD, respostas a impugnações) e organizar a legislação vigente em um só lugar, com foco na **Lei 14.133/2021**.

---

## Funcionalidades

- **Geração de documentos**: criação dinâmica de Termos de Referência, ETP, DFD e respostas a impugnações.
- **Modelos personalizáveis**: tags substituídas automaticamente por dados do cliente/usuário.
- **Área do usuário**: login de servidores/empresas, acesso a histórico de documentos.
- **Painel administrativo**: gestão de modelos e conteúdos.
- **Infraestrutura preparada**: escalável, segura, pronta para integração futura com APIs externas (ex.: IA para análise de editais).

---

## Stack Tecnológica

- **Backend**: Django (Python 3.11+)
- **Banco de dados**: PostgreSQL
- **Frontend**: Django Templates + Bootstrap/Tailwind
- **Servidor web**: Nginx + Gunicorn
---

## Instalação e Uso

### 1. Clonar o repositório
```bash
git clone https://github.com/adryantaborda/mdlicitatech-system.git
cd MDLicitatech
