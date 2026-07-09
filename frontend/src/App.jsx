import { useState, useEffect } from 'react'
import './App.css'

const API_URL = 'https://cijene-app.onrender.com'
//const API_URL = 'http://127.0.0.1:8000'

function App() {
  const [query, setQuery] = useState('')
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(false)

  const [selectedProduct, setSelectedProduct] = useState(null)
  const [prices, setPrices] = useState([])

  const [selectedChain, setSelectedChain] = useState('')
  const [selectedCity, setSelectedCity] = useState('')
  const [sortOrder, setSortOrder] = useState('asc')

  const [chains, setChains] = useState([])
  const [cities, setCities] = useState([])

  useEffect(() => {
    async function loadFilters() {
      try {
        const chainsResponse = await fetch(`${API_URL}/chains`)
        const chainsData = await chainsResponse.json()
        setChains(chainsData)

        const citiesResponse = await fetch(`${API_URL}/cities`)
        const citiesData = await citiesResponse.json()
        setCities(citiesData)
      } catch (error) {
        console.error('Greška kod dohvaćanja filtera:', error)
      }
    }

    loadFilters()
  }, [])

  useEffect(() => {
    if (query.length < 2) {
      setProducts([])
      setLoading(false)
      return
    }

    if (selectedProduct && query === selectedProduct.name) {
      return
    }

    setSelectedProduct(null)
    setPrices([])
    setSelectedChain('')
    setSelectedCity('')
    setSortOrder('asc')

    const timeoutId = setTimeout(async () => {
      setLoading(true)

      try {
        const response = await fetch(
          `${API_URL}/search?query=${encodeURIComponent(query)}&limit=10`
        )

        const data = await response.json()
        setProducts(data)
      } catch (error) {
        console.error('Greška kod dohvaćanja proizvoda:', error)
        setProducts([])
      } finally {
        setLoading(false)
      }
    }, 400)

    return () => clearTimeout(timeoutId)
  }, [query, selectedProduct])

  function handleSearchChange(value) {
    setQuery(value)
  }

  async function selectProduct(
    product,
    chain = selectedChain,
    city = selectedCity,
    sort = sortOrder
  ) {
    setSelectedProduct(product)
    setQuery(product.name)
    setProducts([])
    setPrices([])

    let url = `${API_URL}/product/${product.barcode}/prices?sort=${sort}`

    if (chain) {
      url += `&chain=${encodeURIComponent(chain)}`
    }

    if (city) {
      url += `&city=${encodeURIComponent(city)}`
    }

    const response = await fetch(url)
    const data = await response.json()

    setPrices(data)
  }

  function resetFilters() {
    setSelectedChain('')
    setSelectedCity('')
    setSortOrder('asc')
    selectProduct(selectedProduct, '', '', 'asc')
  }

  const validPrices = prices.filter((item) => item.price !== null)

  const minPrice =
    validPrices.length > 0
      ? Math.min(...validPrices.map((item) => item.price))
      : null

  const maxPrice =
    validPrices.length > 0
      ? Math.max(...validPrices.map((item) => item.price))
      : null

  const priceDifference =
    minPrice !== null && maxPrice !== null
      ? maxPrice - minPrice
      : null

  return (
    <div className="app">
      <h1>Usporedba cijena proizvoda</h1>
      <p>Pretraži proizvod i pronađi gdje je najjeftiniji.</p>

      <input
        type="text"
        placeholder="Upiši naziv proizvoda, npr. jogurt"
        value={query}
        onChange={(e) => handleSearchChange(e.target.value)}
      />

      {loading && <p>Učitavanje...</p>}

      <div className="results">
        {products.map((product) => (
          <div
            className="product-card"
            key={product.barcode}
            onClick={() => selectProduct(product)}
          >
            <h3>{product.name}</h3>
            <p>{product.brand}</p>
            <p>{product.quantity}</p>
          </div>
        ))}
      </div>

      {selectedProduct && (
        <div>
          <h2>{selectedProduct.name}</h2>

          <div className="filters">
            <select
              value={selectedChain}
              onChange={(e) => {
                setSelectedChain(e.target.value)
                selectProduct(selectedProduct, e.target.value, selectedCity, sortOrder)
              }}
            >
              <option value="">Svi lanci</option>

              {chains.map((chain) => (
                <option key={chain} value={chain}>
                  {chain.charAt(0).toUpperCase() + chain.slice(1)}
                </option>
              ))}
            </select>

            <select
              value={selectedCity}
              onChange={(e) => {
                setSelectedCity(e.target.value)
                selectProduct(selectedProduct, selectedChain, e.target.value, sortOrder)
              }}
            >
              <option value="">Svi gradovi</option>

              {cities.map((city) => (
                <option key={city} value={city}>
                  {city}
                </option>
              ))}
            </select>

            <select
              value={sortOrder}
              onChange={(e) => {
                setSortOrder(e.target.value)
                selectProduct(selectedProduct, selectedChain, selectedCity, e.target.value)
              }}
            >
              <option value="asc">Najjeftinije prvo</option>
              <option value="desc">Najskuplje prvo</option>
            </select>

            <button type="button" onClick={resetFilters}>
              Resetiraj filtre
            </button>
          </div>

          {validPrices.length > 0 && (
            <div className="stats">
              <div className="stat-card">
                <span>Najniža cijena</span>
                <strong>{minPrice.toFixed(2)} €</strong>
              </div>

              <div className="stat-card">
                <span>Najviša cijena</span>
                <strong>{maxPrice.toFixed(2)} €</strong>
              </div>

              <div className="stat-card">
                <span>Razlika</span>
                <strong>{priceDifference.toFixed(2)} €</strong>
              </div>

              <div className="stat-card">
                <span>Broj trgovina</span>
                <strong>{validPrices.length}</strong>
              </div>
            </div>
          )}

          <table>
            <thead>
              <tr>
                <th>Lanac</th>
                <th>Grad</th>
                <th>Adresa</th>
                <th>Cijena</th>
                <th>Količina</th>
                <th>Karta</th>
              </tr>
            </thead>

            <tbody>
              {prices.map((item, index) => (
                <tr
                  key={index}
                  className={
                    item.price !== null && item.price === minPrice
                      ? 'cheapest-row'
                      : ''
                  }
                >
                  <td>{item.chain}</td>
                  <td>{item.city}</td>
                  <td>{item.address}</td>
                  <td>{item.price} €</td>
                  <td>{item.quantity}</td>
                  <td>
                    <a
                      href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                        item.address + ' ' + item.city
                      )}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Prikaži
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default App