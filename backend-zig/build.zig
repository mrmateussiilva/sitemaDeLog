const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Criar módulo
    const root_module = b.addModule("logparser", .{
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });

    // Shared library usando addLibrary
    const lib = b.addLibrary(.{
        .name = "logparser",
        .root_module = root_module,
        .linkage = .dynamic,
    });

    b.installArtifact(lib);
}

