# Phishing Detection System - User Manual

## Overview

The Phishing Detection System is a comprehensive security solution that helps identify and prevent phishing attacks across multiple modalities: text, URLs, images, and graph analysis. This manual provides step-by-step instructions for using the system effectively.

## Getting Started

### Accessing the System

1. **Web Interface**: Open your browser and navigate to `http://localhost:5173`
2. **API Endpoints**: Use the REST API at `http://localhost:8000`
3. **Browser Extension**: Install the Chrome extension for real-time protection

### System Requirements

- **Browser**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **JavaScript**: Enabled
- **Network**: Internet connection for model downloads
- **Screen Resolution**: 1024x768 minimum (1920x1080 recommended)

## Web Interface Guide

### Dashboard Overview

The main dashboard provides an overview of the system status and recent activity:

- **System Health**: Shows the status of all services
- **Recent Detections**: Lists recent phishing detections
- **Performance Metrics**: Displays response times and accuracy
- **Quick Actions**: Access to common functions

### Text Analysis

#### Step 1: Access Text Analysis
1. Click on "Text Analysis" in the main menu
2. Or navigate directly to the text analysis page

#### Step 2: Input Text
1. Paste or type the text you want to analyze in the text area
2. The system supports up to 10,000 characters
3. Click "Analyze" to start the analysis

#### Step 3: Review Results
The system will display:
- **Phishing Status**: Whether the text is classified as phishing
- **Confidence Score**: How confident the system is (0-100%)
- **Reasons**: Why the text was classified as phishing
- **Processing Time**: How long the analysis took

#### Example Analysis
```
Input: "Your account has been compromised. Click here to verify: http://fake-bank.com/login"

Results:
✅ Phishing Detected
Confidence: 95%
Reasons:
- Urgent language detected
- Suspicious URL in text
- Account compromise claim
Processing Time: 45ms
```

### URL Analysis

#### Step 1: Access URL Analysis
1. Click on "URL Analysis" in the main menu
2. Or navigate directly to the URL analysis page

#### Step 2: Input URL
1. Enter the URL you want to analyze
2. The system supports HTTP and HTTPS URLs
3. Click "Analyze" to start the analysis

#### Step 3: Review Results
The system will display:
- **Phishing Status**: Whether the URL is classified as phishing
- **Confidence Score**: How confident the system is (0-100%)
- **Reasons**: Why the URL was classified as phishing
- **Features**: Technical features extracted from the URL
- **Fusion Sources**: Results from different detection methods

#### Example Analysis
```
Input: "http://fake-bank.com/login"

Results:
✅ Phishing Detected
Confidence: 87%
Reasons:
- Suspicious domain structure
- High entropy in URL
- No SSL certificate
Features:
- Length: 25 characters
- Entropy: 3.2
- DNS Records: 1
- SSL Expiry: 30 days
Fusion Sources:
- Scanner: 80%
- HF Model: 90%
- OTX: 0%
- Graph: 70%
Processing Time: 78ms
```

### Image Analysis

#### Step 1: Access Image Analysis
1. Click on "Image Analysis" in the main menu
2. Or navigate directly to the image analysis page

#### Step 2: Upload Image
1. Click "Choose File" to select an image
2. Supported formats: JPG, PNG, GIF, BMP
3. Maximum file size: 10MB
4. Click "Analyze" to start the analysis

#### Step 3: Review Results
The system will display:
- **Phishing Status**: Whether the image is classified as phishing
- **Confidence Score**: How confident the system is (0-100%)
- **Reasons**: Why the image was classified as phishing
- **Detected Brands**: Brands identified in the image
- **Extracted URLs**: URLs found in the image
- **Visual Indicators**: Visual features that indicate phishing

#### Example Analysis
```
Input: Screenshot of fake PayPal login page

Results:
✅ Phishing Detected
Confidence: 92%
Reasons:
- Form layout detected
- Brand mismatch identified
- Warning overlay present
Detected Brands: PayPal, Microsoft
Extracted URLs:
- http://fake-paypal.com/login
- http://suspicious-site.com/verify
Visual Indicators:
- Form Layout: 80%
- Color Mismatch: 60%
- Warning Overlay: 90%
Processing Time: 156ms
```

### Graph Analysis

#### Step 1: Access Graph Analysis
1. Click on "Graph Analysis" in the main menu
2. Or navigate directly to the graph analysis page

#### Step 2: Input Graph Data
1. Enter nodes (entities) in the graph
2. Define relationships (edges) between nodes
3. Specify relationship types
4. Click "Analyze" to start the analysis

#### Step 3: Review Results
The system will display:
- **Phishing Status**: Whether the graph pattern is classified as phishing
- **Confidence Score**: How confident the system is (0-100%)
- **Anomaly Score**: How anomalous the pattern is (0-100%)
- **Patterns Detected**: Specific patterns identified
- **Processing Time**: How long the analysis took

#### Example Analysis
```
Input:
Nodes: [user1, user2, suspicious_domain]
Edges: [
  {from: user1, to: user2, type: communication},
  {from: user2, to: suspicious_domain, type: access}
]

Results:
✅ Phishing Detected
Confidence: 88%
Anomaly Score: 75%
Patterns Detected:
- Suspicious communication pattern
- Unusual access pattern to domain
Processing Time: 67ms
```

## Browser Extension

### Installation
1. Download the extension from the Chrome Web Store
2. Click "Add to Chrome"
3. Confirm the installation

### Usage
1. The extension automatically scans web pages
2. A warning icon appears if phishing is detected
3. Click the icon to view detailed analysis
4. The extension blocks access to confirmed phishing sites

### Configuration
1. Right-click the extension icon
2. Select "Options"
3. Configure detection sensitivity
4. Set up notifications
5. Manage whitelist/blacklist

### Features
- **Real-time Protection**: Automatic scanning of web pages
- **URL Blocking**: Prevents access to phishing sites
- **Visual Warnings**: Clear warnings for detected threats
- **Detailed Analysis**: Access to full analysis results
- **Customizable Settings**: Adjustable sensitivity and behavior

## API Usage

### Authentication
Currently, the API does not require authentication. For production use, implement API key authentication.

### Rate Limits
- **Text Analysis**: 100 requests per minute
- **URL Analysis**: 100 requests per minute
- **Image Analysis**: 50 requests per minute
- **Graph Analysis**: 100 requests per minute

### Example API Calls

#### Text Analysis
```bash
curl -X POST "http://localhost:8000/analyze_text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Your account has been compromised. Click here to verify."}'
```

#### URL Analysis
```bash
curl -X POST "http://localhost:8000/analyze_url" \
  -H "Content-Type: application/json" \
  -d '{"url": "http://fake-bank.com/login"}'
```

#### Image Analysis
```bash
curl -X POST "http://localhost:8000/analyze_screenshot" \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="}'
```

## Best Practices

### Text Analysis
1. **Include Context**: Provide full text context for better analysis
2. **Check URLs**: Analyze URLs separately for comprehensive results
3. **Review Results**: Always review results before taking action
4. **Update Regularly**: Keep the system updated for latest threat patterns

### URL Analysis
1. **Verify Domains**: Check domain reputation before clicking
2. **Look for Red Flags**: Suspicious patterns, typos, unusual domains
3. **Use HTTPS**: Prefer HTTPS URLs when possible
4. **Check Certificates**: Verify SSL certificate validity

### Image Analysis
1. **High Quality**: Use clear, high-resolution images
2. **Full Screenshots**: Include complete page screenshots
3. **Multiple Angles**: Analyze different parts of the image
4. **Brand Verification**: Cross-check with official brand sources

### Graph Analysis
1. **Complete Data**: Provide comprehensive node and edge information
2. **Relationship Types**: Specify accurate relationship types
3. **Historical Context**: Include temporal information when available
4. **Pattern Recognition**: Look for unusual connection patterns

## Troubleshooting

### Common Issues

#### Service Not Responding
1. Check if all services are running
2. Verify network connectivity
3. Check service logs for errors
4. Restart services if necessary

#### Slow Performance
1. Check system resources (CPU, memory)
2. Verify network latency
3. Check for rate limiting
4. Optimize request size

#### Inaccurate Results
1. Verify input data quality
2. Check model version and updates
3. Review confidence thresholds
4. Report false positives/negatives

#### Browser Extension Issues
1. Check extension permissions
2. Verify browser compatibility
3. Update extension to latest version
4. Clear browser cache and cookies

### Getting Help

#### Self-Service
1. **Documentation**: Check this manual and API documentation
2. **Health Checks**: Verify service status at `/health` endpoints
3. **Logs**: Review service logs for error messages
4. **Monitoring**: Check Grafana dashboards for system status

#### Support Channels
1. **Issues**: Report issues in the project repository
2. **Documentation**: See `/docs` directory for detailed guides
3. **Monitoring**: Check service health at `/health` endpoint
4. **Community**: Join the community forum for discussions

## Security Considerations

### Data Privacy
- **Local Processing**: All analysis is performed locally
- **No Data Storage**: Input data is not stored permanently
- **Secure Communication**: All API calls use HTTPS
- **Access Control**: Implement proper authentication

### Best Practices
- **Input Validation**: Validate all input data
- **Output Sanitization**: Sanitize all output data
- **Regular Updates**: Keep system and models updated
- **Monitoring**: Monitor for security events

## Performance Tips

### Optimization
1. **Batch Requests**: Use batch endpoints for multiple analyses
2. **Caching**: Cache results for identical requests
3. **Async Processing**: Use asynchronous processing for large datasets
4. **Resource Management**: Monitor and optimize resource usage

### Monitoring
1. **Response Times**: Monitor API response times
2. **Error Rates**: Track error rates and types
3. **Throughput**: Monitor requests per second
4. **Resource Usage**: Check CPU, memory, and disk usage

## Advanced Features

### Continuous Learning
The system automatically learns from new threats:
- **Model Updates**: Regular model retraining
- **Performance Monitoring**: Continuous performance tracking
- **Feedback Integration**: User feedback incorporation
- **Threat Intelligence**: Integration with threat feeds

### Customization
- **Threshold Tuning**: Adjust detection sensitivity
- **Model Selection**: Choose appropriate models
- **Feature Configuration**: Enable/disable specific features
- **Integration Options**: Custom integration capabilities

## Conclusion

The Phishing Detection System provides comprehensive protection against phishing attacks across multiple modalities. By following this manual and implementing best practices, you can effectively use the system to protect against evolving threats.

For additional support or questions, refer to the documentation or contact the support team.
