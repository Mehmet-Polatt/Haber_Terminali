import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  Linking,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import client from '../api/client';
import * as Clipboard from 'expo-clipboard';

const THEME = {
  bg: '#F6F4F0',
  text: '#000000',
  gray: '#737373',
  lightGray: '#E5E5E5',
};

const DEFAULT_IMAGES = {
  tbmm: require('../../assets/yaldizli_logo.png'),
  politics: require('../../assets/turkbayragi.jpg'),
  football: require('../../assets/futbol.png'),
};

const getDefaultImage = (cat, src = '') => {
  const s = src ? src.toLowerCase() : '';
  if (cat === 'tbmm' || s.includes('tbmm')) {
    return DEFAULT_IMAGES.tbmm;
  }
  if (
    cat === 'politics' ||
    s.includes('bbc') ||
    s.includes('t24') ||
    s.includes('sabah') ||
    s.includes('sözcü') ||
    s.includes('oksijen') ||
    s.includes('politika')
  ) {
    return DEFAULT_IMAGES.politics;
  }
  if (
    cat === 'football' ||
    s.includes('gzt') ||
    s.includes('sporx') ||
    s.includes('dha') ||
    s.includes('radar') ||
    s.includes('ntv') ||
    s.includes('spor')
  ) {
    return DEFAULT_IMAGES.football;
  }
  return null;
};

const Card = ({ card, category, onUpdate }) => {
  const {
    id,
    title,
    summary,
    original_url,
    image_url,
    source,
    is_analyzed,
    replaces_or_differs_from,
    technical_tradeoffs,
    rational_arguments,
    historical_background,
    core_concept,
    concept_definition,
    today_summary,
  } = card;

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [imgLoadError, setImgLoadError] = useState(false);

  const defaultImage = getDefaultImage(category, source);
  const showNetworkImage = !!image_url && !imgLoadError;

  const handleReadMore = () => {
    if (original_url) {
      Linking.openURL(original_url);
    }
  };

  const handleAnalyzeAction = async () => {
    if (is_analyzed) {
      let promptText = `Şu haber hakkında seninle daha derin bir tartışma yapmak istiyorum. Başlık: ${title}. Kaynak: ${original_url}. Bana bu konunun arkasındaki detayları anlatır mısın?`;
      try {
        await Clipboard.setStringAsync(promptText);
        Alert.alert(
          'Prompt Kopyalandı!',
          'Özel prompt kopyalandı! Gemini açıldığında mesaj kutusuna yapıştırarak sohbete başlayabilirsiniz.',
          [
            {
              text: "Gemini'ı Aç 🚀",
              onPress: () => {
                Linking.openURL('https://gemini.google.com/app');
              },
            },
          ]
        );
      } catch (err) {
        Alert.alert('Kopyalama Hatası', 'Metin panoya kopyalanırken bir hata oluştu.');
      }
      return;
    }

    // Trigger AI Analysis
    setIsAnalyzing(true);
    let endpoint = `/api/cards/${id}/analyze`;
    if (category === 'football') endpoint = `/api/football/cards/${id}/analyze`;
    else if (category === 'politics' || category === 'tbmm') endpoint = `/api/politics/cards/${id}/analyze`;

    try {
      const response = await client.post(endpoint, {}, { timeout: 60000 });
      if (onUpdate) {
        onUpdate(response.data);
      }
    } catch (error) {
      console.log('HATA DETAYI:', error.response?.data);
      const errorDetail = error.response?.data?.detail || error.message || 'Bilinmeyen bir hata oluştu.';
      Alert.alert('Analiz Başarısız', `Yapay zeka analizi gerçekleştirilirken bir sorun oluştu.\n\nHata: ${errorDetail}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <View style={styles.cardContainer}>
      {/* Image Section */}
      {showNetworkImage ? (
        <Image
          source={{ uri: image_url }}
          style={styles.cardImage}
          onError={() => setImgLoadError(true)}
        />
      ) : defaultImage ? (
        <View style={styles.defaultImageWrapper}>
          <Image
            source={defaultImage}
            style={[
              styles.cardImage,
              (category === 'tbmm' || category === 'football') && styles.containImage,
            ]}
            resizeMode={(category === 'tbmm' || category === 'football') ? 'contain' : 'cover'}
          />
        </View>
      ) : (
        <View style={styles.imagePlaceholder}>
          <Feather name="image" size={32} color={THEME.gray} />
        </View>
      )}

      {/* Content Section */}
      <View style={styles.contentContainer}>
        {source ? <Text style={styles.sourceText}>{source}</Text> : null}
        <Text style={styles.titleText} numberOfLines={3}>
          {title}
        </Text>

        {/* If Analyzed, show the analysis results instead of plain summary */}
        {is_analyzed ? (
          <View style={styles.analysisContainer}>
            {(today_summary || summary) && (
              <View style={styles.analysisSection}>
                <Text style={styles.analysisLabel}>Bugün Ne Oldu?</Text>
                <Text style={styles.analysisText}>{today_summary || summary}</Text>
              </View>
            )}

            {replaces_or_differs_from && (
              <View style={styles.analysisSection}>
                <Text style={styles.analysisLabel}>Farkı & Trade-off</Text>
                <Text style={styles.analysisText}>{replaces_or_differs_from}</Text>
              </View>
            )}

            {rational_arguments && (
              <View style={styles.analysisSection}>
                <Text style={styles.analysisLabel}>Rasyonel Argümanlar</Text>
                <Text style={styles.analysisText}>{rational_arguments}</Text>
              </View>
            )}

            {core_concept && (
              <View style={styles.analysisSection}>
                <Text style={styles.analysisLabel}>Kavram: {core_concept}</Text>
                <Text style={styles.analysisText}>{concept_definition}</Text>
              </View>
            )}
          </View>
        ) : summary ? (
          <Text style={styles.summaryText} numberOfLines={2}>
            {summary}
          </Text>
        ) : null}

        {/* Footer: Read More & Button */}
        <View style={styles.footerRow}>
          <TouchableOpacity onPress={handleReadMore} activeOpacity={0.7}>
            <Text style={styles.readMoreText}>read more</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionBtn}
            onPress={handleAnalyzeAction}
            activeOpacity={0.8}
            disabled={isAnalyzing}
          >
            {isAnalyzing ? (
              <ActivityIndicator size="small" color="#FFF" />
            ) : (
              <Feather
                name={is_analyzed ? 'message-square' : 'arrow-up-right'}
                size={20}
                color="#FFF"
              />
            )}
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  cardContainer: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    marginBottom: 24,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: THEME.lightGray,
  },
  cardImage: {
    width: '100%',
    height: 200,
    resizeMode: 'cover',
  },
  containImage: {
    padding: 16,
  },
  defaultImageWrapper: {
    width: '100%',
    height: 200,
    backgroundColor: '#F8F9FA',
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
  },
  imagePlaceholder: {
    width: '100%',
    height: 200,
    backgroundColor: THEME.lightGray,
    justifyContent: 'center',
    alignItems: 'center',
  },
  contentContainer: {
    padding: 24,
  },
  sourceText: {
    fontSize: 12,
    fontWeight: '700',
    color: THEME.gray,
    textTransform: 'uppercase',
    marginBottom: 8,
  },
  titleText: {
    fontSize: 22,
    fontWeight: '800',
    color: THEME.text,
    lineHeight: 28,
    marginBottom: 12,
  },
  summaryText: {
    fontSize: 15,
    color: THEME.gray,
    lineHeight: 22,
    marginBottom: 24,
  },
  analysisContainer: {
    marginBottom: 24,
    gap: 12,
  },
  analysisSection: {
    backgroundColor: THEME.bg,
    padding: 12,
    borderRadius: 12,
    borderLeftWidth: 3,
    borderLeftColor: THEME.text,
  },
  analysisLabel: {
    fontSize: 12,
    fontWeight: '800',
    textTransform: 'uppercase',
    color: THEME.text,
    marginBottom: 4,
  },
  analysisText: {
    fontSize: 14,
    color: THEME.text,
    lineHeight: 20,
  },
  footerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
  },
  readMoreText: {
    fontSize: 14,
    fontWeight: '700',
    color: THEME.text,
    textDecorationLine: 'underline',
  },
  actionBtn: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: THEME.text,
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default Card;
