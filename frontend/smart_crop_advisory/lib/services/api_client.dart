import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

typedef UnauthorizedHandler = Future<void> Function();

class ApiException implements Exception {
  final int? statusCode;
  final String message;

  const ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class ApiClient {
  static const baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8002/api/v1',
  );

  final http.Client _client;
  final UnauthorizedHandler? _onUnauthorized;

  ApiClient({http.Client? client, UnauthorizedHandler? onUnauthorized})
    : _client = client ?? http.Client(),
      _onUnauthorized = onUnauthorized;

  Uri _uri(String path) {
    final normalizedBase = baseUrl.replaceFirst(RegExp(r'/+$'), '');
    return Uri.parse(
      '$normalizedBase/${path.replaceFirst(RegExp(r'^/+'), '')}',
    );
  }

  Future<Map<String, dynamic>> getObject(String path, {String? token}) async {
    final response = await _client
        .get(_uri(path), headers: _headers(token))
        .timeout(const Duration(seconds: 20));
    final value = await _decode(response, hasToken: token != null);
    if (value is Map<String, dynamic>) return value;
    throw const ApiException('The server returned an unexpected response.');
  }

  Future<List<dynamic>> getList(String path, {String? token}) async {
    final response = await _client
        .get(_uri(path), headers: _headers(token))
        .timeout(const Duration(seconds: 20));
    final value = await _decode(response, hasToken: token != null);
    if (value is List<dynamic>) return value;
    throw const ApiException('The server returned an unexpected response.');
  }

  Future<Map<String, dynamic>> postJson(
    String path,
    Map<String, dynamic> body, {
    String? token,
  }) async {
    final response = await _client
        .post(
          _uri(path),
          headers: _headers(token, contentType: 'application/json'),
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 20));
    final value = await _decode(response, hasToken: token != null);
    if (value is Map<String, dynamic>) return value;
    throw const ApiException('The server returned an unexpected response.');
  }

  Future<Map<String, dynamic>> patchJson(
    String path,
    Map<String, dynamic> body, {
    String? token,
  }) async {
    final response = await _client
        .patch(
          _uri(path),
          headers: _headers(token, contentType: 'application/json'),
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 20));
    final value = await _decode(response, hasToken: token != null);
    if (value is Map<String, dynamic>) return value;
    throw const ApiException('The server returned an unexpected response.');
  }

  Future<Map<String, dynamic>> postForm(
    String path,
    Map<String, String> fields,
  ) async {
    final response = await _client
        .post(
          _uri(path),
          headers: _headers(
            null,
            contentType: 'application/x-www-form-urlencoded',
          ),
          body: fields,
        )
        .timeout(const Duration(seconds: 20));
    final value = await _decode(response, hasToken: false);
    if (value is Map<String, dynamic>) return value;
    throw const ApiException('The server returned an unexpected response.');
  }

  Future<Map<String, dynamic>> postMultipartFile(
    String path, {
    required String fileName,
    required List<int> bytes,
  }) async {
    final request = http.MultipartRequest('POST', _uri(path));
    request.headers.addAll(_headers(null));
    request.files.add(
      http.MultipartFile.fromBytes('file', bytes, filename: fileName),
    );

    final streamedResponse = await _client
        .send(request)
        .timeout(const Duration(seconds: 120));
    final response = await http.Response.fromStream(streamedResponse);
    final value = await _decode(response, hasToken: false);
    if (value is Map<String, dynamic>) return value;
    throw const ApiException('The server returned an unexpected response.');
  }

  Map<String, String> _headers(String? token, {String? contentType}) {
    return {
      'Content-Type': ?contentType,
      'Authorization': ?(token == null ? null : 'Bearer $token'),
      'Accept': 'application/json',
    };
  }

  Future<dynamic> _decode(
    http.Response response, {
    required bool hasToken,
  }) async {
    dynamic value;
    if (response.body.isNotEmpty) {
      try {
        value = jsonDecode(response.body);
      } on FormatException {
        value = null;
      }
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      if (response.statusCode == 401 && hasToken) {
        await _onUnauthorized?.call();
      }
      final detail = value is Map<String, dynamic> ? value['detail'] : null;
      throw ApiException(
        _errorMessage(detail, response.statusCode),
        statusCode: response.statusCode,
      );
    }
    return value;
  }

  String _errorMessage(dynamic detail, int statusCode) {
    if (detail is String && detail.isNotEmpty) return detail;
    if (detail is List) {
      final messages = detail
          .whereType<Map>()
          .map((item) => item['msg'])
          .whereType<String>()
          .toList();
      if (messages.isNotEmpty) return messages.join(' ');
    }
    if (statusCode >= 500) return 'The server could not complete the request.';
    return 'Request failed (HTTP $statusCode).';
  }
}
