const std = @import("std");
const csv_parser = @import("csv_parser.zig");

// Função auxiliar para encontrar valor após uma chave HTML
fn encontrarValor(html: []const u8, chave: []const u8) ?[]const u8 {
    const chave_completa = std.fmt.allocPrint(std.heap.page_allocator, "<th>{s}</th>", .{chave}) catch return null;
    defer std.heap.page_allocator.free(chave_completa);

    if (std.mem.indexOf(u8, html, chave_completa)) |pos_inicio| {
        const pos_fim_chave = pos_inicio + chave_completa.len;
        if (std.mem.indexOfPos(u8, html, pos_fim_chave, "<td>")) |pos_td_inicio| {
            const inicio_valor = pos_td_inicio + 4; // "<td>".len
            if (std.mem.indexOfPos(u8, html, inicio_valor, "</td>")) |pos_td_fim| {
                return html[inicio_valor..pos_td_fim];
            }
        }
    }
    return null;
}

// Extrair altura de uma dimensão "largura x altura cm"
fn extrairAltura(dimensao: []const u8) ?f64 {
    // Buscar padrão "x" e "cm"
    if (std.mem.indexOf(u8, dimensao, " x ")) |pos_x| {
        const parte_direita = dimensao[pos_x + 3..];
        if (std.mem.indexOf(u8, parte_direita, " cm")) |pos_cm| {
            const altura_str = std.mem.trim(u8, parte_direita[0..pos_cm], " \t\n\r");
            const altura = std.fmt.parseFloat(f64, altura_str) catch return null;
            return altura;
        }
    }
    return null;
}

// Limpar nome de arquivo (remover caminho)
fn limparNome(caminho: []const u8) []const u8 {
    // Encontrar última barra ou backslash
    var ultima_barra: ?usize = null;
    for (caminho, 0..) |c, i| {
        if (c == '/' or c == '\\') {
            ultima_barra = i;
        }
    }
    
    if (ultima_barra) |pos| {
        return caminho[pos + 1..];
    }
    return caminho;
}

// Processar um arquivo HTML individual
export fn processarHtml(
    caminho_html: [*:0]const u8,
    caminho_json_saida: [*:0]const u8,
) i32 {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Ler arquivo HTML
    const caminho_html_slice = std.mem.sliceTo(caminho_html, 0);
    const arquivo = std.fs.cwd().openFile(caminho_html_slice, .{}) catch return -1;
    defer arquivo.close();

    const tamanho = arquivo.getEndPos() catch return -1;
    const conteudo_html = arquivo.readToEndAlloc(allocator, tamanho) catch return -1;
    defer allocator.free(conteudo_html);

    // Converter de latin-1 para UTF-8 (simplificado - assumindo que já está em UTF-8 ou compatível)
    // Na prática, pode precisar de conversão real de encoding

    // Buscar valores
    const arquivo_valor = encontrarValor(conteudo_html, "ARQUIVO:") orelse return -1;
    const dimensao_valor = encontrarValor(conteudo_html, "DIMENSÃO:") orelse return -1;
    const data_valor = encontrarValor(conteudo_html, "INÍCIO, DATA E HORA DO RIP:") orelse return -1;
    const copias_valor = encontrarValor(conteudo_html, "QUANTIDADE DE CÓPIAS:") orelse return -1;

    // Limpar valores (remover espaços)
    const arquivo_limpo = std.mem.trim(u8, arquivo_valor, " \t\n\r");
    const dimensao_limpa = std.mem.trim(u8, dimensao_valor, " \t\n\r");
    const data_limpa = std.mem.trim(u8, data_valor, " \t\n\r");
    const copias_str = std.mem.trim(u8, copias_valor, " \t\n\r");

    // Parsear quantidade de cópias
    const copias = std.fmt.parseInt(i32, copias_str, 10) catch return -1;

    // Extrair altura e calcular metros
    const altura = extrairAltura(dimensao_limpa) orelse return -1;
    const metros = (altura * @as(f64, @floatFromInt(copias))) / 100.0;

    // Limpar nome do arquivo
    const nome_arquivo = limparNome(arquivo_limpo);

    // Criar JSON (formato simples e direto)
    var json_buffer = std.ArrayList(u8).initCapacity(allocator, 1024) catch return -1;
    defer json_buffer.deinit(allocator);

    const json_writer = json_buffer.writer(allocator);
    json_writer.print(
        \\[
        \\  {{
        \\    "nome_arquivo": "{s}",
        \\    "metros": {d:.2},
        \\    "data_impressao": "{s}"
        \\  }}
        \\]
    , .{ nome_arquivo, metros, data_limpa }) catch return -1;

    // Escrever JSON no arquivo de saída
    const caminho_json_slice = std.mem.sliceTo(caminho_json_saida, 0);
    const arquivo_json = std.fs.cwd().createFile(caminho_json_slice, .{}) catch return -1;
    defer arquivo_json.close();

    arquivo_json.writeAll(json_buffer.items) catch return -1;

    return 0;
}

// Processar um arquivo CSV individual
export fn processarCsv(
    caminho_csv: [*:0]const u8,
    caminho_json_saida: [*:0]const u8,
) i32 {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Ler e processar CSV
    const caminho_csv_slice = std.mem.sliceTo(caminho_csv, 0);
    const json_content = csv_parser.processarCsvParaJson(allocator, caminho_csv_slice) catch return -1;
    defer allocator.free(json_content);

    // Escrever JSON no arquivo de saída
    const caminho_json_slice = std.mem.sliceTo(caminho_json_saida, 0);
    const arquivo_json = std.fs.cwd().createFile(caminho_json_slice, .{}) catch return -1;
    defer arquivo_json.close();

    arquivo_json.writeAll(json_content) catch return -1;

    return 0;
}

// Processar diretório inteiro
export fn processarDiretorio(
    path_origem: [*:0]const u8,
    path_destino: [*:0]const u8,
) i32 {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const origem_slice = std.mem.sliceTo(path_origem, 0);
    const destino_slice = std.mem.sliceTo(path_destino, 0);

    // Abrir diretório de origem
    var dir_origem = std.fs.cwd().openDir(origem_slice, .{ .iterate = true }) catch return -1;
    defer dir_origem.close();

    // Criar diretório de destino se não existir
    std.fs.cwd().makePath(destino_slice) catch {};

    var resultados = std.ArrayList(u8).initCapacity(allocator, 4096) catch return -1;
    defer resultados.deinit(allocator);
    const writer = resultados.writer(allocator);
    writer.print("[", .{}) catch return -1;

    var primeiro = true;
    var iterador = dir_origem.iterate();
    while (iterador.next() catch return -1) |entry| {
        if (entry.kind != .file) continue;
        
        const nome = entry.name;
        const is_html = std.mem.endsWith(u8, nome, ".html") or std.mem.endsWith(u8, nome, ".HTML");
        const is_csv = std.mem.endsWith(u8, nome, ".csv") or std.mem.endsWith(u8, nome, ".CSV");
        
        if (!is_html and !is_csv) {
            continue;
        }

        // Construir caminhos completos
        const caminho_arquivo = std.fmt.allocPrint(allocator, "{s}/{s}", .{ origem_slice, nome }) catch return -1;
        defer allocator.free(caminho_arquivo);

        const nome_base = nome[0..std.mem.lastIndexOfScalar(u8, nome, '.') orelse nome.len];
        const caminho_json_temp = std.fmt.allocPrint(allocator, "{s}/{s}.json", .{ destino_slice, nome_base }) catch return -1;
        defer allocator.free(caminho_json_temp);

        // Processar arquivo (HTML ou CSV)
        const caminho_arquivo_c = allocator.dupeZ(u8, caminho_arquivo) catch return -1;
        defer allocator.free(caminho_arquivo_c);
        const caminho_json_c = allocator.dupeZ(u8, caminho_json_temp) catch return -1;
        defer allocator.free(caminho_json_c);

        const resultado = if (is_html)
            processarHtml(caminho_arquivo_c, caminho_json_c)
        else
            processarCsv(caminho_arquivo_c, caminho_json_c);

        if (resultado != 0) {
            continue; // Pula arquivos com erro
        }

        // Ler JSON gerado e adicionar ao array
        const arquivo_json = std.fs.cwd().openFile(caminho_json_temp, .{}) catch continue;
        defer arquivo_json.close();
        const tamanho_json = arquivo_json.getEndPos() catch continue;
        const conteudo_json = arquivo_json.readToEndAlloc(allocator, tamanho_json) catch continue;
        defer allocator.free(conteudo_json);

        // Remover colchetes externos do JSON individual
        // O JSON individual tem formato: [\n  {...}\n]
        // Precisamos extrair apenas o objeto {...}
        var inicio_obj: ?usize = null;
        var fim_obj: ?usize = null;
        
        // Encontrar início do objeto (primeiro '{' após '[')
        if (std.mem.indexOf(u8, conteudo_json, "{")) |pos| {
            inicio_obj = pos;
        }
        
        // Encontrar fim do objeto (último '}' antes de ']')
        if (std.mem.lastIndexOf(u8, conteudo_json, "}")) |pos| {
            fim_obj = pos + 1;
        }
        
        if (inicio_obj == null or fim_obj == null or inicio_obj.? >= fim_obj.?) {
            continue; // JSON inválido, pular
        }
        
        const conteudo_limpo = conteudo_json[inicio_obj.?..fim_obj.?];

        if (!primeiro) {
            writer.print(",", .{}) catch return -1;
        }
        primeiro = false;
        writer.print("\n  {s}", .{conteudo_limpo}) catch return -1;
    }

    writer.print("\n]", .{}) catch return -1;

    // Escrever JSON consolidado
    const caminho_resultado = std.fmt.allocPrint(allocator, "{s}/resultado.json", .{destino_slice}) catch return -1;
    defer allocator.free(caminho_resultado);
    
    const arquivo_final = std.fs.cwd().createFile(caminho_resultado, .{}) catch return -1;
    defer arquivo_final.close();
    arquivo_final.writeAll(resultados.items) catch return -1;

    return 0;
}

// Calcular metros de uma dimensão
export fn calcularMetros(
    dimensao_str: [*:0]const u8,
    quantidade_copias: i32,
) f64 {
    const dimensao_slice = std.mem.sliceTo(dimensao_str, 0);
    const altura = extrairAltura(dimensao_slice) orelse return 0.0;
    return (altura * @as(f64, @floatFromInt(quantidade_copias))) / 100.0;
}

// Limpar nome de arquivo (remover caminho)
export fn limparNomeArquivo(
    caminho_completo: [*:0]const u8,
    buffer_saida: [*]u8,
    tamanho_buffer: i32,
) i32 {
    const caminho_slice = std.mem.sliceTo(caminho_completo, 0);
    const nome_limpo = limparNome(caminho_slice);

    if (nome_limpo.len >= @as(usize, @intCast(tamanho_buffer))) {
        return -1; // Buffer muito pequeno
    }

    @memcpy(buffer_saida[0..nome_limpo.len], nome_limpo);
    buffer_saida[nome_limpo.len] = 0; // Null terminator

    return 0;
}

