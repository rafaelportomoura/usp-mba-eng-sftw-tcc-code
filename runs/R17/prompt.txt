Você está em um diretório de trabalho de um projeto Python que usa somente a biblioteca padrão. Ele contém um módulo com defeitos ou funcionalidades incompletas, o arquivo REQUIREMENTS.md e testes públicos na pasta tests/.

Tarefa:
1. Leia REQUIREMENTS.md.
2. Altere o módulo para atender a todos os requisitos, mantendo os nomes públicos e as assinaturas descritos.
3. Adicione ou ajuste testes em tests/ para verificar a sua implementação.
4. Execute a suíte com `python -m unittest discover -s tests -t .` e corrija o que falhar.

Restrições:
- Use apenas a biblioteca padrão do Python.
- Trabalhe somente neste diretório.
- Não há ninguém disponível para esclarecer dúvidas; decida com base em REQUIREMENTS.md e no código existente.
- Você dispõe de cerca de 12 minutos.

A entrega é a alteração feita neste diretório.

Relatório final obrigatório:
Ao concluir, sua mensagem final deve conter um relatório em português com as seis seções abaixo, nesta ordem e com estes títulos:
1. Resumo da solução: o que foi alterado e onde.
2. Premissas adotadas: interpretações e decisões tomadas onde o enunciado era omisso ou ambíguo.
3. Riscos, limitações e pontos não verificados: o que pode falhar ou não foi testado.
4. Justificativa técnica e alternativas relevantes: por que a solução foi escolhida e quais alternativas pertinentes existiam.
5. Rastreabilidade: tabela Markdown com as colunas `Requisito`, `Arquivo e símbolo`, `Teste`, com uma linha para cada requisito de REQUIREMENTS.md.
6. Comandos executados e resultados: os comandos de verificação que você rodou e o que cada um retornou.
Inclua somente conteúdo verificável a partir do código, dos testes e dos comandos que você executou.
