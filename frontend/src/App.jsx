import { useState, useEffect, useRef } from 'react'
import './App.css'

const API_URL = 'https://cijene-app.onrender.com'
//const API_URL = 'http://127.0.0.1:8000'
const PRICE_BATCH_SIZE = 20

function App() {
  const [query, setQuery] = useState('')
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(false)

  const [selectedProduct, setSelectedProduct] = useState(null)
  const [prices, setPrices] = useState([])
  const [visiblePriceCount, setVisiblePriceCount] = useState(PRICE_BATCH_SIZE)

  const [selectedChains, setSelectedChains] = useState([])
  const [selectedCities, setSelectedCities] = useState([])
  const [sortOrder, setSortOrder] = useState('asc')
  const [openDropdown, setOpenDropdown] = useState(null)
  const filtersRef = useRef(null)

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
    function closeDropdowns(event) {
      if (filtersRef.current && !filtersRef.current.contains(event.target)) {
        setOpenDropdown(null)
      }
    }

    document.addEventListener('mousedown', closeDropdowns)
    return () => document.removeEventListener('mousedown', closeDropdowns)
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
    setSelectedChains([])
    setSelectedCities([])
    setSortOrder('asc')

    const controller = new AbortController()
    const timeoutId = setTimeout(async () => {
      setLoading(true)

      try {
        const response = await fetch(
          `${API_URL}/search?query=${encodeURIComponent(query)}&limit=10`,
          { signal: controller.signal }
        )

        const data = await response.json()
        setProducts(data)
      } catch (error) {
        if (error.name === 'AbortError') {
          return
        }
        console.error('Greška kod dohvaćanja proizvoda:', error)
        setProducts([])
      } finally {
        setLoading(false)
      }
    }, 400)

    return () => {
      clearTimeout(timeoutId)
      controller.abort()
    }
  }, [query, selectedProduct])

  function handleSearchChange(value) {
    setOpenDropdown(null)
    setVisiblePriceCount(PRICE_BATCH_SIZE)
    setQuery(value)
  }

  async function selectProduct(
    product,
    chains = selectedChains,
    cities = selectedCities,
    sort = sortOrder
  ) {
    setVisiblePriceCount(PRICE_BATCH_SIZE)
    setSelectedProduct(product)
    setQuery(product.name)
    setProducts([])
    setPrices([])

    let url = `${API_URL}/product/${product.barcode}/prices?sort=${sort}`

    for (const chain of chains) {
      url += `&chain=${encodeURIComponent(chain)}`
    }

    for (const city of cities) {
      url += `&city=${encodeURIComponent(city)}`
    }

    const response = await fetch(url)
    const data = await response.json()

    setPrices(data)
  }

  function resetFilters() {
    setOpenDropdown(null)
    setSelectedChains([])
    setSelectedCities([])
    setSortOrder('asc')
    selectProduct(selectedProduct, [], [], 'asc')
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
            key={product.id}
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

          <div className="filters" ref={filtersRef}>
            <div className="filter-dropdown">
              <button
                type="button"
                className="filter-trigger"
                aria-expanded={openDropdown === 'chains'}
                onClick={() => setOpenDropdown(openDropdown === 'chains' ? null : 'chains')}
              >
                {selectedChains.length === 0
                  ? 'Svi lanci'
                  : selectedChains.length === 1
                    ? selectedChains[0].charAt(0).toUpperCase() + selectedChains[0].slice(1)
                    : `${selectedChains.length} lanca`}
              </button>
              {openDropdown === 'chains' && (
                <div className="filter-menu">
                  {chains.map((chain) => (
                    <label className="filter-option" key={chain}>
                      <input
                        type="checkbox"
                        checked={selectedChains.includes(chain)}
                        onChange={() => {
                          const values = selectedChains.includes(chain)
                            ? selectedChains.filter((value) => value !== chain)
                            : [...selectedChains, chain]
                          setSelectedChains(values)
                          selectProduct(selectedProduct, values, selectedCities, sortOrder)
                        }}
                      />
                      <span>{chain.charAt(0).toUpperCase() + chain.slice(1)}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div className="filter-dropdown">
              <button
                type="button"
                className="filter-trigger"
                aria-expanded={openDropdown === 'cities'}
                onClick={() => setOpenDropdown(openDropdown === 'cities' ? null : 'cities')}
              >
                {selectedCities.length === 0
                  ? 'Svi gradovi'
                  : selectedCities.length === 1
                    ? selectedCities[0]
                    : `${selectedCities.length} grada`}
              </button>
              {openDropdown === 'cities' && (
                <div className="filter-menu">
                  {cities.map((city) => (
                    <label className="filter-option" key={city}>
                      <input
                        type="checkbox"
                        checked={selectedCities.includes(city)}
                        onChange={() => {
                          const values = selectedCities.includes(city)
                            ? selectedCities.filter((value) => value !== city)
                            : [...selectedCities, city]
                          setSelectedCities(values)
                          selectProduct(selectedProduct, selectedChains, values, sortOrder)
                        }}
                      />
                      <span>{city}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <select
              value={sortOrder}
              onChange={(e) => {
                setSortOrder(e.target.value)
                selectProduct(selectedProduct, selectedChains, selectedCities, e.target.value)
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

          <div className="table-container">
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
              {prices.slice(0, visiblePriceCount).map((item, index) => (
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

          {visiblePriceCount < prices.length && (
            <div className="filters">
              <button
                type="button"
                onClick={() => setVisiblePriceCount((count) => count + PRICE_BATCH_SIZE)}
              >
                Prikaži još
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default App
