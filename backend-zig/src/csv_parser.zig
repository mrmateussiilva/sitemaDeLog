const std = @import("std");

// Estrutura temporária para armazenar dados de uma impressão CSV
const ImpressaoCsv = struct {
    nome_arquivo: []const u8,
    metros: f64,
    data_impressao: []const u8,
};

// Processar arquivo CSV e retornar JSON no mesmo formato do HTML
pub fn processarCsvParaJson(
    allocator: std.mem.Allocator,
    caminho_csv: []const u8,
) ![]const u8 {
    // Ler arquivo CSV
    const arquivo = std.fs.cwd().openFile(caminho_csv, .{}) catch return error.FileNotFound;
    defer arquivo.close();

    const tamanho = arquivo.getEndPos() catch return error.FileReadError;
    const conteudo_csv = arquivo.readToEndAlloc(allocator, tamanho) catch return error.OutOfMemory;
    defer allocator.free(conteudo_csv);

    // Parsear CSV
    var impressoes = std.ArrayList(ImpressaoCsv).initCapacity(allocator, 100) catch return error.OutOfMemory;
    defer {
        for (impressoes.items) |*imp| {
            allocator.free(imp.nome_arquivo);
            allocator.free(imp.data_impressao);
        }
        impressoes.deinit(allocator);
    }

    var linhas = std.mem.splitSequence(u8, conteudo_csv, "\n");

    // Pular header (primeira linha)
    _ = linhas.next();

    // Processar cada linha
    while (linhas.next()) |linha| {
        const linha_trim = std.mem.trim(u8, linha, " \t\r\n");
        if (linha_trim.len == 0) continue;

        const impressao = parseCsvLine(allocator, linha_trim) catch {
            // Ignora linhas com erro e continua
            continue;
        };
        impressoes.append(allocator, impressao) catch continue;
    }

    // Gerar JSON no mesmo formato do HTML
    var json_buffer = std.ArrayList(u8).initCapacity(allocator, 4096) catch return error.OutOfMemory;
    defer json_buffer.deinit(allocator);

    const json_writer = json_buffer.writer(allocator);
    json_writer.print("[", .{}) catch return error.JsonWriteError;

    for (impressoes.items, 0..) |imp, i| {
        if (i > 0) {
            json_writer.print(",", .{}) catch return error.JsonWriteError;
        }
        json_writer.print(
            \\\n  {{
            \\    "nome_arquivo": "{s}",
            \\    "metros": {d:.2},
            \\    "data_impressao": "{s}"
            \\  }}
        , .{ imp.nome_arquivo, imp.metros, imp.data_impressao }) catch return error.JsonWriteError;
    }

    json_writer.print("\n]", .{}) catch return error.JsonWriteError;

    // Retornar string JSON (caller deve fazer free)
    return json_buffer.toOwnedSlice(allocator);
}

// Parsear uma linha CSV
// Formato esperado: Data,Hora,Arquivo,Largura,Altura,Unidade,Copias
// Exemplo: 03/01/2024,07:47:47,PAINEL PATRULHA CANINA 11.tif,158.0,158.0,cm,1
fn parseCsvLine(
    allocator: std.mem.Allocator,
    linha: []const u8,
) !ImpressaoCsv {
    var campos = std.mem.splitSequence(u8, linha, ",");

    const data = campos.next() orelse return error.InvalidFormat;
    const hora = campos.next() orelse return error.InvalidFormat;
    const arquivo = campos.next() orelse return error.InvalidFormat;
    _ = campos.next() orelse return error.InvalidFormat; // largura (não usado)
    const altura_str = campos.next() orelse return error.InvalidFormat;
    const unidade = campos.next() orelse return error.InvalidFormat;
    const copias_str = campos.next() orelse return error.InvalidFormat;

    // Limpar espaços
    const data_limpa = std.mem.trim(u8, data, " \"\t");
    const hora_limpa = std.mem.trim(u8, hora, " \"\t");
    const arquivo_limpo = std.mem.trim(u8, arquivo, " \"\t");
    const altura_limpa = std.mem.trim(u8, altura_str, " \"\t");
    const unidade_limpa = std.mem.trim(u8, unidade, " \"\t");
    const copias_limpa = std.mem.trim(u8, copias_str, " \"\t");

    // Parsear números (largura não é usada, apenas altura)
    var altura = std.fmt.parseFloat(f64, altura_limpa) catch return error.InvalidNumber;
    const copias = std.fmt.parseInt(i32, copias_limpa, 10) catch return error.InvalidNumber;

    // Converter para cm se necessário
    if (std.mem.eql(u8, unidade_limpa, "in") or 
        std.mem.eql(u8, unidade_limpa, "IN") or
        std.mem.eql(u8, unidade_limpa, "inch") or
        std.mem.eql(u8, unidade_limpa, "inches")) {
        altura = altura * 2.54;
    }

    // Calcular metros: (altura_cm × quantidade_cópias) / 100
    const metros = (altura * @as(f64, @floatFromInt(copias))) / 100.0;

    // Construir data_hora no formato "HH:MM:SS DD/MM/YYYY"
    // Formato CSV: Data = "DD/MM/YYYY", Hora = "HH:MM:SS"
    const data_hora = try std.fmt.allocPrint(
        allocator,
        "{s} {s}",
        .{ hora_limpa, data_limpa }
    );

    // Limpar nome do arquivo (remover caminho se houver)
    const nome_arquivo = limparNomeArquivo(arquivo_limpo);
    const nome_arquivo_dup = try allocator.dupe(u8, nome_arquivo);

    return ImpressaoCsv{
        .nome_arquivo = nome_arquivo_dup,
        .metros = metros,
        .data_impressao = data_hora,
    };
}

// Limpar nome de arquivo (remover caminho)
fn limparNomeArquivo(caminho: []const u8) []const u8 {
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

