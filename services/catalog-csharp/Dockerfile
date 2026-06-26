# ---- build ----
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src
COPY Catalog.csproj .
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /app

# ---- runtime ----
FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS runtime
WORKDIR /app
COPY --from=build /app .
# data/catalog mounted/copied to /data/catalog for the seeder
ENV ASPNETCORE_URLS=http://+:8080
ENV SEED_DIR=/data/catalog
EXPOSE 8080
ENTRYPOINT ["dotnet", "Catalog.dll"]
