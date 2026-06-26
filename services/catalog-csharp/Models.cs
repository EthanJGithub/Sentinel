using System.ComponentModel.DataAnnotations;
using System.Text.Json;

namespace Sentinel.Catalog;

// ---------------------------------------------------------------------------
// EF Core entities (the C# service is the system of record for catalog,
// contract pricing, stock and orders -- the "existing established product"
// the AI agent must work *through*).
// ---------------------------------------------------------------------------

public class Product
{
    [Key] public string Sku { get; set; } = default!;
    public string Name { get; set; } = default!;
    public string Category { get; set; } = default!;
    public string Subcategory { get; set; } = default!;
    public string Vendor { get; set; } = default!;
    public string Unit { get; set; } = "each";
    public decimal ListPrice { get; set; }
    public int StockOnHand { get; set; }
    public bool Compliant { get; set; } = true;

    /// <summary>Rooms this SKU applies to, e.g. ["resident_room","bathroom"].</summary>
    public List<string> ApplicableRooms { get; set; } = new();

    /// <summary>Compliance-relevant attributes (clear_width_in, covers_toilet_bath, ...)
    /// stored as JSONB so the agent's validate_item tool can reason over them.</summary>
    public Dictionary<string, JsonElement> Attributes { get; set; } = new();

    public List<ContractPrice> ContractPrices { get; set; } = new();
}

public class Contract
{
    [Key] public string Id { get; set; } = default!;
    public string GpoName { get; set; } = default!;
    public decimal Discount { get; set; }
    public List<ContractPrice> Prices { get; set; } = new();
}

public class ContractPrice
{
    [Key] public int Id { get; set; }
    public string Sku { get; set; } = default!;
    public Product Product { get; set; } = default!;
    public string ContractId { get; set; } = default!;
    public Contract Contract { get; set; } = default!;
    public decimal Price { get; set; }
}

public class Order
{
    [Key] public Guid Id { get; set; } = Guid.NewGuid();
    public string PlanId { get; set; } = default!;
    public string FacilityName { get; set; } = "";
    public decimal Total { get; set; }
    public string Status { get; set; } = "PLACED";
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
    public List<OrderLine> Lines { get; set; } = new();
}

public class OrderLine
{
    [Key] public int Id { get; set; }
    public Guid OrderId { get; set; }
    public string Sku { get; set; } = default!;
    public int Qty { get; set; }
    public decimal UnitPrice { get; set; }
    public string? ContractId { get; set; }
}

// ---------------------------------------------------------------------------
// DTOs for the HTTP API consumed by the Python agent + MCP server.
// ---------------------------------------------------------------------------

public record ProductDto(
    string Sku, string Name, string Category, string Subcategory, string Vendor,
    string Unit, decimal ListPrice, int StockOnHand, bool Compliant,
    List<string> ApplicableRooms, Dictionary<string, JsonElement> Attributes,
    decimal BestPrice, string? BestContractId)
{
    public static ProductDto From(Product p)
    {
        var best = p.ContractPrices.OrderBy(cp => cp.Price).FirstOrDefault();
        return new ProductDto(p.Sku, p.Name, p.Category, p.Subcategory, p.Vendor, p.Unit,
            p.ListPrice, p.StockOnHand, p.Compliant, p.ApplicableRooms, p.Attributes,
            best?.Price ?? p.ListPrice, best?.ContractId);
    }
}

public record PriceRequest(List<string> Skus, string? ContractId);
public record PriceLine(string Sku, decimal ListPrice, decimal BestPrice, string? ContractId, decimal SavingsPct);

public record PlaceOrderRequest(string PlanId, string FacilityName, List<OrderLineRequest> Lines);
public record OrderLineRequest(string Sku, int Qty, string? ContractId);
