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

const PAGE_SIZE = 20; // Sayfa başına haber sayısı
import { Feather } from '@expo/vector-icons';
import client from './src/api/client';
import Card from './src/components/Card';

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

export default function App() {
  const [activeCategory, setActiveCategory] = useState('tech');
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);
  const skipRef = useRef(0); // Mevcut sayfa offset'i
  const isFetchingRef = useRef(false); // Paralel istek kilidi

  const getEndpoint = (category) => {
    if (category === 'politics') return '/api/politics/cards';
    if (category === 'football') return '/api/football/cards';
    if (category === 'tbmm') return '/api/tbmm/cards';
    return '/api/cards';
  };

  // İlk yükleme veya pull-to-refresh: listeyi sıfırlar
  const fetchCards = useCallback(async (category = activeCategory, isRefresh = false) => {
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;

    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setErrorMsg(null);

    try {
      const response = await client.get(getEndpoint(category), {
        params: { limit: PAGE_SIZE, skip: 0 },
      });
      const data = response.data;
      setCards(data);
      skipRef.current = data.length;
      setHasMore(data.length === PAGE_SIZE);
    } catch (error) {
      console.error('Failed to fetch cards:', error);
      setErrorMsg('Haberler yüklenemedi. Lütfen tekrar deneyin.');
    } finally {
      setLoading(false);
      setRefreshing(false);
      isFetchingRef.current = false;
    }
  }, [activeCategory]);

  // Sonsuz scroll: liste sonuna gelindiğinde sonraki sayfayı yükle
  const fetchMoreCards = useCallback(async () => {
    if (isFetchingRef.current || !hasMore || loadingMore) return;
    isFetchingRef.current = true;
    setLoadingMore(true);

    try {
      const response = await client.get(getEndpoint(activeCategory), {
        params: { limit: PAGE_SIZE, skip: skipRef.current },
      });
      const newData = response.data;
      if (newData.length === 0) {
        setHasMore(false);
      } else {
        setCards(prev => [...prev, ...newData]);
        skipRef.current += newData.length;
        setHasMore(newData.length === PAGE_SIZE);
      }
    } catch (error) {
      console.error('Failed to load more cards:', error);
    } finally {
      setLoadingMore(false);
      isFetchingRef.current = false;
    }
  }, [activeCategory, hasMore, loadingMore]);

  // Kategori değişince listeyi ve sayfalama state'ini sıfırla
  useEffect(() => {
    skipRef.current = 0;
    setHasMore(true);
    setCards([]);
    fetchCards(activeCategory);
  }, [activeCategory]);

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
          renderItem={({ item }) => (
            <Card
              card={item}
              category={activeCategory}
              onUpdate={(updatedCard) => {
                setCards(prevCards => prevCards.map(c => c.id === updatedCard.id ? updatedCard : c));
              }}
            />
          )}
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={renderEmptyComponent}
          ListFooterComponent={
            loadingMore ? (
              <View style={styles.footerLoader}>
                <ActivityIndicator size="small" color={THEME.gray} />
                <Text style={styles.footerText}>Daha fazla yükleniyor...</Text>
              </View>
            ) : null
          }
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => fetchCards(activeCategory, true)}
              tintColor={THEME.text}
              colors={[THEME.text]}
            />
          }
          onEndReached={fetchMoreCards}
          onEndReachedThreshold={0.3}
          showsVerticalScrollIndicator={false}
        />
      )}
    </SafeAreaView>
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
    paddingBottom: 32,
  },
  footerLoader: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 16,
    gap: 8,
  },
  footerText: {
    fontSize: 13,
    color: THEME.gray,
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
});
