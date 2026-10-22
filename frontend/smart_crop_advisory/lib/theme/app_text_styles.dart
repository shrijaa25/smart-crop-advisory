import 'package:flutter/material.dart';
import 'app_colors.dart';

class AppText {
  // Keep text available offline. GoogleFonts' runtime fetching left the entire
  // app without visible labels when the browser could not reach its CDN.
  static TextStyle h1 = TextStyle(
    fontFamily: 'Rubik', fontSize: 32, fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
  );
  static TextStyle h2 = TextStyle(
    fontFamily: 'Rubik', fontSize: 24, fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
  );
  static TextStyle h3 = TextStyle(
    fontFamily: 'Rubik', fontSize: 20, fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
  );
  static TextStyle body = TextStyle(
    fontFamily: 'Rubik', fontSize: 16, fontWeight: FontWeight.w400,
    color: AppColors.textPrimary,
  );
  static TextStyle bodyMuted = TextStyle(
    fontFamily: 'Rubik', fontSize: 16, fontWeight: FontWeight.w400,
    color: AppColors.textSecondary,
  );
  static TextStyle small = TextStyle(
    fontFamily: 'Rubik', fontSize: 15, fontWeight: FontWeight.w400,
    color: AppColors.textSecondary,
  );
  static TextStyle label = TextStyle(
    fontFamily: 'Rubik', fontSize: 15, fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
  );
}
