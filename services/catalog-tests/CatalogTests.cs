using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Sentinel.Catalog;
using Xunit;

namespace Sentinel.Catalog.Tests;

public class ProductDtoTests
{
    private static Product Bed(params (string contract, decimal price)[] prices)
    {
        var p = new Product
        {
            Sku = "DS-RES-1001", Name = "RestWell LTC Bed", Category = "resident_bed",
            Subcategory = "Long-Term Care Bed", Vendor = "RestWell", Unit = "each",
            ListPrice = 1800m, StockOnHand = 10, Compliant = true,
            ApplicableRooms = new() { "resident_room" },
        };
        foreach (var (c, pr) in prices)
            p.ContractPrices.Add(new ContractPrice { Sku = p.Sku, ContractId = c, Price = pr });
        return p;
    }

    [Fact]
    public void From_PicksLowestContractPrice()
    {
        var dto = ProductDto.From(Bed(("GPO-PREMIER", 1500m), ("DSSI-DIRECT", 1423m), ("GPO-VIZIENT", 1480m)));
        Assert.Equal(1423m, dto.BestPrice);
        Assert.Equal("DSSI-DIRECT", dto.BestContractId);
    }

    [Fact]
    public void From_FallsBackToListPriceWhenNoContracts()
    {
        var dto = ProductDto.From(Bed());
        Assert.Equal(1800m, dto.BestPrice);
        Assert.Null(dto.BestContractId);
    }

    [Fact]
    public void From_PreservesComplianceAttributesAndRooms()
    {
        var p = Bed(("DSSI-DIRECT", 1423m));
        p.Attributes["entrapment_compliant"] = JsonSerializer.SerializeToElement(true);
        var dto = ProductDto.From(p);
        Assert.True(dto.Attributes["entrapment_compliant"].GetBoolean());
        Assert.Contains("resident_room", dto.ApplicableRooms);
    }
}

public class CatalogDbTests
{
    private static CatalogDb InMemory()
    {
        var opts = new DbContextOptionsBuilder<CatalogDb>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString()).Options;
        return new CatalogDb(opts);
    }

    [Fact]
    public void Order_TotalsLinesCorrectly()
    {
        using var db = InMemory();
        var order = new Order { PlanId = "p1", FacilityName = "Cedarwood" };
        order.Lines.Add(new OrderLine { Sku = "A", Qty = 30, UnitPrice = 100m });
        order.Lines.Add(new OrderLine { Sku = "B", Qty = 5, UnitPrice = 200m });
        order.Total = order.Lines.Sum(l => l.UnitPrice * l.Qty);
        db.Orders.Add(order);
        db.SaveChanges();

        var saved = db.Orders.First();
        Assert.Equal(4000m, saved.Total);   // 30*100 + 5*200
        Assert.Equal(2, saved.Lines.Count);
        Assert.Equal("PLACED", saved.Status);
    }
}
