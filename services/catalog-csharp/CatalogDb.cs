using Microsoft.EntityFrameworkCore;
using System.Text.Json;

namespace Sentinel.Catalog;

public class CatalogDb : DbContext
{
    public CatalogDb(DbContextOptions<CatalogDb> options) : base(options) { }

    public DbSet<Product> Products => Set<Product>();
    public DbSet<Contract> Contracts => Set<Contract>();
    public DbSet<ContractPrice> ContractPrices => Set<ContractPrice>();
    public DbSet<Order> Orders => Set<Order>();
    public DbSet<OrderLine> OrderLines => Set<OrderLine>();

    protected override void OnModelCreating(ModelBuilder b)
    {
        var jsonOpts = new JsonSerializerOptions();

        // Store list/dictionary attributes as JSONB so the agent can reason over them.
        b.Entity<Product>().Property(p => p.ApplicableRooms)
            .HasColumnType("jsonb")
            .HasConversion(
                v => JsonSerializer.Serialize(v, jsonOpts),
                v => JsonSerializer.Deserialize<List<string>>(v, jsonOpts) ?? new());

        b.Entity<Product>().Property(p => p.Attributes)
            .HasColumnType("jsonb")
            .HasConversion(
                v => JsonSerializer.Serialize(v, jsonOpts),
                v => JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(v, jsonOpts) ?? new());

        b.Entity<Product>().Property(p => p.ListPrice).HasColumnType("numeric(12,2)");
        b.Entity<ContractPrice>().Property(p => p.Price).HasColumnType("numeric(12,2)");
        b.Entity<Contract>().Property(p => p.Discount).HasColumnType("numeric(5,4)");

        b.Entity<ContractPrice>()
            .HasOne(cp => cp.Product).WithMany(p => p.ContractPrices)
            .HasForeignKey(cp => cp.Sku);
        b.Entity<ContractPrice>()
            .HasOne(cp => cp.Contract).WithMany(c => c.Prices)
            .HasForeignKey(cp => cp.ContractId);

        b.Entity<Order>().HasMany(o => o.Lines).WithOne().HasForeignKey(l => l.OrderId);
    }
}
