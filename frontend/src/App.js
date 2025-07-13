import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [device, setDevice] = useState(null);
  const [characteristic, setCharacteristic] = useState(null);
  const [currentReading, setCurrentReading] = useState(null);
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('Desconectado');
  const [lastUpdate, setLastUpdate] = useState(null);

  // Load initial data
  useEffect(() => {
    loadLatestReading();
    loadHistory();
    loadStats();
  }, []);

  const loadLatestReading = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/glucose/latest`);
      if (response.ok) {
        const data = await response.json();
        if (data) {
          setCurrentReading(data);
          setLastUpdate(new Date(data.timestamp).toLocaleString('pt-BR'));
        }
      }
    } catch (error) {
      console.error('Erro ao carregar última leitura:', error);
    }
  };

  const loadHistory = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/glucose/history?limit=20`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
      }
    } catch (error) {
      console.error('Erro ao carregar histórico:', error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/glucose/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Erro ao carregar estatísticas:', error);
    }
  };

  const connectToDevice = async () => {
    if (!navigator.bluetooth) {
      alert('Bluetooth não suportado neste navegador. Use Chrome no desktop ou Android.');
      return;
    }

    try {
      setConnectionStatus('Conectando...');
      
      // Request device
      const device = await navigator.bluetooth.requestDevice({
        filters: [{ namePrefix: 'NeoView' }],
        optionalServices: ['12345678-1234-1234-1234-123456789abc']
      });

      setDevice(device);
      
      // Connect to GATT server
      const server = await device.gatt.connect();
      
      // Get service
      const service = await server.getPrimaryService('12345678-1234-1234-1234-123456789abc');
      
      // Get characteristic
      const characteristic = await service.getCharacteristic('87654321-4321-4321-4321-cba987654321');
      
      setCharacteristic(characteristic);
      
      // Start notifications
      await characteristic.startNotifications();
      
      characteristic.addEventListener('characteristicvaluechanged', handleDataReceived);
      
      setIsConnected(true);
      setConnectionStatus('Conectado');
      
      console.log('Dispositivo conectado com sucesso!');
      
    } catch (error) {
      console.error('Erro ao conectar:', error);
      setConnectionStatus('Erro na conexão');
      alert('Erro ao conectar com o dispositivo: ' + error.message);
    }
  };

  const disconnectDevice = async () => {
    if (device && device.gatt.connected) {
      await device.gatt.disconnect();
    }
    setIsConnected(false);
    setDevice(null);
    setCharacteristic(null);
    setConnectionStatus('Desconectado');
  };

  const handleDataReceived = async (event) => {
    try {
      const value = event.target.value;
      const decoder = new TextDecoder();
      const jsonString = decoder.decode(value);
      
      console.log('Dados recebidos:', jsonString);
      
      const data = JSON.parse(jsonString);
      
      if (data.glucose !== undefined) {
        // Send to backend
        const response = await fetch(`${API_BASE_URL}/api/glucose`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            glucose_value: data.glucose,
            timestamp: data.timestamp || new Date().toISOString(),
            device_id: device.name || 'ESP32_NeoView'
          })
        });

        if (response.ok) {
          const savedReading = await response.json();
          setCurrentReading(savedReading);
          setLastUpdate(new Date().toLocaleString('pt-BR'));
          
          // Reload history and stats
          loadHistory();
          loadStats();
        }
      }
    } catch (error) {
      console.error('Erro ao processar dados:', error);
    }
  };

  const simulateReading = async () => {
    // Simulate ESP32 data for testing
    const glucoseValues = [65, 95, 120, 160, 180, 220, 85, 110];
    const randomValue = glucoseValues[Math.floor(Math.random() * glucoseValues.length)];
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/glucose`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          glucose_value: randomValue,
          device_id: 'ESP32_Simulator'
        })
      });

      if (response.ok) {
        const savedReading = await response.json();
        setCurrentReading(savedReading);
        setLastUpdate(new Date().toLocaleString('pt-BR'));
        loadHistory();
        loadStats();
      }
    } catch (error) {
      console.error('Erro ao simular leitura:', error);
    }
  };

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'Hipoglicemia': return '⬇️';
      case 'Normal': return '✅';
      case 'Atenção': return '⚠️';
      case 'Alerta': return '🚨';
      default: return '📊';
    }
  };

  const clearHistory = async () => {
    if (window.confirm('Tem certeza que deseja limpar todo o histórico?')) {
      try {
        await fetch(`${API_BASE_URL}/api/glucose/clear`, { method: 'DELETE' });
        setCurrentReading(null);
        setHistory([]);
        setStats(null);
        setLastUpdate(null);
      } catch (error) {
        console.error('Erro ao limpar histórico:', error);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            🩺 Monitoramento NeoView
          </h1>
          <p className="text-gray-600">Sistema de Monitoramento de Glicose</p>
        </div>

        {/* Connection Status */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-800 mb-2">Status da Conexão</h2>
              <p className={`text-sm font-medium ${isConnected ? 'text-green-600' : 'text-gray-500'}`}>
                {connectionStatus}
              </p>
            </div>
            <div className="space-x-3">
              {!isConnected ? (
                <button
                  onClick={connectToDevice}
                  className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                >
                  📱 Conectar ESP32
                </button>
              ) : (
                <button
                  onClick={disconnectDevice}
                  className="bg-red-500 hover:bg-red-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                >
                  🔌 Desconectar
                </button>
              )}
              <button
                onClick={simulateReading}
                className="bg-green-500 hover:bg-green-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
              >
                🧪 Simular Leitura
              </button>
            </div>
          </div>
        </div>

        {/* Current Reading */}
        {currentReading && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Leitura Atual</h2>
            <div className="text-center">
              <div 
                className="inline-block px-8 py-6 rounded-xl text-white font-bold text-3xl mb-4"
                style={{ backgroundColor: currentReading.color }}
              >
                {getCategoryIcon(currentReading.category)} {currentReading.glucose_value} mg/dL
              </div>
              <p className="text-lg font-semibold text-gray-700 mb-2">
                {currentReading.category}
              </p>
              <p className="text-sm text-gray-500">
                Última atualização: {lastUpdate}
              </p>
            </div>
          </div>
        )}

        {/* Stats */}
        {stats && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Estatísticas</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <p className="text-2xl font-bold text-blue-600">{stats.total_readings}</p>
                <p className="text-sm text-gray-600">Total de Leituras</p>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <p className="text-2xl font-bold text-green-600">{stats.average_glucose}</p>
                <p className="text-sm text-gray-600">Média de Glicose</p>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-sm space-y-1">
                  {Object.entries(stats.category_distribution || {}).map(([category, count]) => (
                    <div key={category} className="flex justify-between">
                      <span>{category}:</span>
                      <span className="font-semibold">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* History */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-800">Histórico de Leituras</h2>
            <button
              onClick={clearHistory}
              className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm transition-colors"
            >
              🗑️ Limpar
            </button>
          </div>
          
          {history.length > 0 ? (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {history.map((reading) => (
                <div 
                  key={reading.id}
                  className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div 
                      className="w-4 h-4 rounded-full"
                      style={{ backgroundColor: reading.color }}
                    ></div>
                    <span className="font-medium">{reading.glucose_value} mg/dL</span>
                    <span className="text-sm text-gray-600">{reading.category}</span>
                  </div>
                  <span className="text-sm text-gray-500">
                    {new Date(reading.timestamp).toLocaleString('pt-BR')}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-gray-500 py-8">
              Nenhuma leitura encontrada. Conecte o ESP32 ou simule uma leitura.
            </p>
          )}
        </div>

        {/* Instructions */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mt-6">
          <h3 className="text-lg font-semibold text-yellow-800 mb-3">📋 Instruções de Uso</h3>
          <div className="text-sm text-yellow-700 space-y-2">
            <p><strong>1.</strong> Configure seu ESP32 com o nome "NeoView" e UUID do serviço: 12345678-1234-1234-1234-123456789abc</p>
            <p><strong>2.</strong> Characteristic UUID: 87654321-4321-4321-4321-cba987654321</p>
            <p><strong>3.</strong> Envie dados JSON no formato: {"glucose": 120, "timestamp": "2025-03-15T10:30:00"}</p>
            <p><strong>4.</strong> Use "Simular Leitura" para testar o sistema antes de conectar o dispositivo real</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;