# Listar todas as tabelas do Dataset
tabelas = list(client.list_tables(dataset_id))

print(f"Total de tabelas encontradas no dataset '{dataset_id}': {len(tabelas)}")

if tabelas:
    print("Nomes das tabelas:")
    for tabela in tabelas:
        print(f" - {tabela.table_id}")
else:
    print("O dataset está vazio.")