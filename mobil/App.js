import 'react-native-gesture-handler';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  FlatList,
  ActivityIndicator,
  RefreshControl,
  SafeAreaView,
  StatusBar,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Feather } from '@expo/vector-icons';
import client from './src/api/client';
import Card from './src/components/Card';

const Tab = createBottomTabNavigator();

// --- THEME ---
const THEME = {
  bg: '#F6F4F0',
  text: '#000000',
  gray: '#737373',
  lightGray: '#E5E5E5',
};

const CATEGORIES = [
  { id: 'tech', label: 'Teknoloji' },
  { id: 'politics', label: 'Siyaset' },
  { id: 'football', label: 'Futbol' },
  { id: 'tbmm', label: 'TBMM' },
];

// --- SCREENS ---

function NewsScreen() {
  const [activeCategory, setActiveCategory] = useState('tech');
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const hasRefreshedOnOpen = useRef(false);

  const fetchCards = useCallback(async (category = activeCategory, isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setErrorMsg(null);

    let endpoint = '/api/cards';
    if (category === 'politics') endpoint = '/api/politics/cards';
    else if (category === 'football') endpoint = '/api/football/cards';
    else if (category === 'tbmm') endpoint = '/api/tbmm/cards';

    try {
      const response = await client.get(endpoint, {
        params: { limit: 20, skip: 0 },
      });
      setCards(response.data);
    } catch (error) {
      console.error('Failed to fetch cards:', error);
      setErrorMsg('Haberler yüklenemedi. Lütfen tekrar deneyin.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [activeCategory]);

  useEffect(() => {
    if (!hasRefreshedOnOpen.current) {
      hasRefreshedOnOpen.current = true;
      client.post('/api/refresh')
        .catch((error) => console.error('Failed to refresh news on app open:', error))
        .finally(() => fetchCards(activeCategory));
      return;
    }
    fetchCards(activeCategory);
  }, [activeCategory, fetchCards]);

  const handleCategoryPress = (categoryId) => {
    if (categoryId !== activeCategory) {
      setActiveCategory(categoryId);
    }
  };

  const renderEmptyComponent = () => {
    if (loading) return null;
    return (
      <View style={styles.emptyContainer}>
        {errorMsg ? (
          <>
            <Text style={styles.errorText}>{errorMsg}</Text>
            <TouchableOpacity style={styles.retryButton} onPress={() => fetchCards(activeCategory)}>
              <Text style={styles.retryButtonText}>Tekrar Dene</Text>
            </TouchableOpacity>
          </>
        ) : (
          <Text style={styles.emptyText}>Haber bulunamadı.</Text>
        )}
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={THEME.bg} />
      
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Haberler</Text>
        <TouchableOpacity style={styles.searchIcon}>
          <Feather name="search" size={24} color={THEME.text} />
        </TouchableOpacity>
      </View>

      <View style={styles.categoryContainer}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categoryScroll}>
          {CATEGORIES.map((cat) => (
            <TouchableOpacity
              key={cat.id}
              style={[styles.categoryBtn, activeCategory === cat.id && styles.categoryBtnActive]}
              onPress={() => handleCategoryPress(cat.id)}
            >
              <Text style={[styles.categoryText, activeCategory === cat.id && styles.categoryTextActive]}>
                {cat.label}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {loading && !refreshing ? (
        <View style={styles.loaderContainer}>
          <ActivityIndicator size="large" color={THEME.text} />
        </View>
      ) : (
        <FlatList
          data={cards}
          keyExtractor={(item) => item.id.toString()}
          renderItem={({ item }) => <Card card={item} category={activeCategory} onUpdate={(updatedCard) => {
            setCards(prevCards => prevCards.map(c => c.id === updatedCard.id ? updatedCard : c));
          }} />}
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={renderEmptyComponent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => fetchCards(activeCategory, true)}
              tintColor={THEME.text}
              colors={[THEME.text]}
            />
          }
          showsVerticalScrollIndicator={false}
        />
      )}
    </SafeAreaView>
  );
}

function MarketsScreen() {
  const [activeTab, setActiveTab] = useState('overview');
  
  // Dummy data for market indices
  const marketIndices = [
    { id: '1', symbol: 'BIST 100', value: '9,450.25', change: '+1.2%', up: true },
    { id: '2', symbol: 'USD/TRY', value: '31.25', change: '-0.1%', up: false },
    { id: '3', symbol: 'EUR/TRY', value: '34.10', change: '+0.3%', up: true },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={THEME.bg} />
      
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Markets</Text>
      </View>

      <View style={styles.segmentContainer}>
        {['overview', 'commodities', 'indices'].map(tab => (
          <TouchableOpacity 
            key={tab} 
            style={[styles.segmentBtn, activeTab === tab && styles.segmentBtnActive]}
            onPress={() => setActiveTab(tab)}
          >
            <Text style={[styles.segmentText, activeTab === tab && styles.segmentTextActive]}>
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.marketCardsContainer}>
        <FlatList
          data={marketIndices}
          horizontal
          showsHorizontalScrollIndicator={false}
          keyExtractor={item => item.id}
          renderItem={({item}) => (
            <View style={styles.marketCard}>
              <Text style={styles.marketSymbol}>{item.symbol}</Text>
              <Text style={styles.marketValue}>{item.value}</Text>
              <Text style={[styles.marketChange, { color: item.up ? '#10B981' : '#EF4444' }]}>
                {item.change}
              </Text>
            </View>
          )}
        />
      </View>

      <Text style={styles.sectionTitle}>Market News</Text>
      
      {/* Mocking list items for market news based on reference image */}
      <View style={styles.marketNewsList}>
        {[1,2,3].map((i) => (
          <View key={i} style={styles.marketNewsItem}>
             <View style={styles.marketNewsImagePlaceholder} />
             <View style={styles.marketNewsTextContainer}>
                <Text style={styles.marketNewsTitle} numberOfLines={2}>
                  Market update: Key indices show strong performance this quarter.
                </Text>
                <Text style={styles.marketNewsDetail}>Today • 2 min read</Text>
             </View>
          </View>
        ))}
      </View>

    </SafeAreaView>
  );
}

// --- NAVIGATION ---

export default function App() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarShowLabel: false,
          tabBarStyle: {
            backgroundColor: THEME.bg,
            borderTopWidth: 0,
            elevation: 0,
            height: 80,
          },
          tabBarIcon: () => {
            let iconName;
            if (route.name === 'News') iconName = 'book-open';
            else if (route.name === 'Markets') iconName = 'trending-up';
            else if (route.name === 'Saved') iconName = 'bookmark';
            else if (route.name === 'Profile') iconName = 'user';

            return (
              <View style={styles.tabIconContainer}>
                <Feather name={iconName} size={24} color={THEME.text} />
              </View>
            );
          },
        })}
      >
        <Tab.Screen name="News" component={NewsScreen} />
        <Tab.Screen name="Markets" component={MarketsScreen} />
        <Tab.Screen name="Saved" component={NewsScreen} />
        <Tab.Screen name="Profile" component={NewsScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

// --- STYLES ---

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.bg,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 10,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '800',
    color: THEME.text,
  },
  searchIcon: {
    padding: 8,
  },
  categoryContainer: {
    marginBottom: 10,
  },
  categoryScroll: {
    paddingHorizontal: 24,
    gap: 12,
  },
  categoryBtn: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    backgroundColor: THEME.lightGray,
  },
  categoryBtnActive: {
    backgroundColor: THEME.text,
  },
  categoryText: {
    fontSize: 14,
    fontWeight: '600',
    color: THEME.gray,
  },
  categoryTextActive: {
    color: THEME.bg,
  },
  listContent: {
    padding: 24,
    paddingTop: 10,
    paddingBottom: 40,
  },
  loaderContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyContainer: {
    padding: 24,
    alignItems: 'center',
  },
  emptyText: {
    color: THEME.gray,
    fontSize: 16,
  },
  errorText: {
    color: '#EF4444',
    textAlign: 'center',
    marginBottom: 16,
  },
  retryButton: {
    padding: 12,
    backgroundColor: THEME.text,
    borderRadius: 8,
  },
  retryButtonText: {
    color: THEME.bg,
    fontWeight: 'bold',
  },
  
  // Tab Bar Styles
  tabIconContainer: {
    padding: 8,
  },

  // Markets Screen Styles
  segmentContainer: {
    flexDirection: 'row',
    paddingHorizontal: 24,
    marginBottom: 24,
  },
  segmentBtn: {
    marginRight: 20,
    paddingVertical: 8,
  },
  segmentBtnActive: {
    borderBottomWidth: 2,
    borderBottomColor: THEME.text,
  },
  segmentText: {
    fontSize: 16,
    color: THEME.gray,
    fontWeight: '500',
  },
  segmentTextActive: {
    color: THEME.text,
    fontWeight: '700',
  },
  marketCardsContainer: {
    paddingLeft: 24,
    marginBottom: 32,
  },
  marketCard: {
    backgroundColor: '#FFFFFF',
    padding: 20,
    borderRadius: 20,
    marginRight: 16,
    width: 140,
    borderWidth: 1,
    borderColor: THEME.lightGray,
  },
  marketSymbol: {
    fontSize: 16,
    fontWeight: '700',
    color: THEME.text,
    marginBottom: 8,
  },
  marketValue: {
    fontSize: 20,
    fontWeight: '800',
    color: THEME.text,
    marginBottom: 4,
  },
  marketChange: {
    fontSize: 14,
    fontWeight: '600',
  },
  sectionTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: THEME.text,
    marginHorizontal: 24,
    marginBottom: 16,
  },
  marketNewsList: {
    paddingHorizontal: 24,
  },
  marketNewsItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: THEME.lightGray,
  },
  marketNewsImagePlaceholder: {
    width: 60,
    height: 60,
    borderRadius: 12,
    backgroundColor: THEME.lightGray,
    marginRight: 16,
  },
  marketNewsTextContainer: {
    flex: 1,
  },
  marketNewsTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: THEME.text,
    marginBottom: 6,
    lineHeight: 20,
  },
  marketNewsDetail: {
    fontSize: 12,
    color: THEME.gray,
  },
});
