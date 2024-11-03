from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from django.contrib import auth, messages
from django.contrib.auth import authenticate
from drf_yasg.utils import swagger_auto_schema
from django.views.decorators.csrf import csrf_exempt

from .wallet.wallet import send_tokensBSC
from .blocks import get_current_or_create_open_block
from .wallet.wallet import (
    generate_ethereum_wallet,
    get_idea_balance,
    get_matter_balance,
    get_idea_info,
    get_matter_info,
    get_bnb_info,
)
from .forms import (
    LoginForm,
    MakeBetForm,
    RegisterForm,
    SellForm,
)
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    MakeBetSerializer,
    SellSerializer,
    TransactionSerializer,
    RemoveBetSerializer
)
from .models import UserProfile, Transaction, Bet
from .dex.dex import get_gas_price_in_usdt
from .const import (
    APP_WALLET,
    APP_WALLET_PRIVATE_KEY,
    MATTER_TOKEN_ADDRESS,
    IDEA_TOKEN_ADDRESS,
)

@swagger_auto_schema(
    method='post',
    request_body=LoginSerializer
)
@api_view(['POST'])
def login(request: Request) -> Response:
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    user = authenticate(request, username=username, password=password)

    if user is None:
        return Response({'error': 'Invalid username or password.'}, status=status.HTTP_401_UNAUTHORIZED)

    auth.login(request, user)
    return Response({'message': f'Successfully logged in as {user.username}.'}, status=status.HTTP_200_OK)


@api_view(['GET'])
def logout(request: Request) -> Response:
    if request.user.is_anonymous:
        return Response({'error': 'You are not logged in.'}, status=status.HTTP_400_BAD_REQUEST)

    auth.logout(request)
    return Response({'message': 'You have successfully logged out.'}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=RegisterSerializer
)
@api_view(['POST'])
def register(request: Request) -> Response:
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()
    auth.login(request, user)

    user_profile = UserProfile.objects.get(user=user)

    wallet = generate_ethereum_wallet()

    user_profile.crypto_wallet_private_key = wallet["private_key"]
    user_profile.crypto_wallet_address = wallet["address"]

    user_profile.save()
    return Response({'message': 'User registered successfully', 'username': user.username},
                    status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bets(request: Request) -> Response:
    user_profile = UserProfile.objects.get(user=request.user)

    try:
        idea_info = get_idea_info(user_profile.crypto_wallet_address)
        matter_info = get_matter_info(user_profile.crypto_wallet_address)
        matter_balance = float(matter_info["balance_formatted"] if matter_info else 0)
        idea_balance = float(idea_info["balance_formatted"] if idea_info else 0)

        bet_list = Bet.objects.filter(
            user=request.user, deleted_at__isnull=True, is_active=True
        ).order_by("created_at")
        bet_data = MakeBetSerializer(bet_list, many=True).data

        gas_price = get_gas_price_in_usdt()
        bnb_info = get_bnb_info(user_profile.crypto_wallet_address)
        bnb_balance = float(bnb_info["balance_formatted"] if bnb_info else 0)
        app_wallet_balance = get_bnb_info(APP_WALLET)["balance_formatted"]

        response_data = {
            "app_wallet": app_wallet_balance,
            "gas_price": gas_price,
            "bet_list": bet_data,
            "user_matter_balance": matter_balance,
            "user_idea_balance": idea_balance,
            "user_bnb_balance": bnb_balance,
        }
        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Could not fetch bets.\n{e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@swagger_auto_schema(
    method='post',
    request_body=MakeBetSerializer
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_bet(request: Request) -> Response:
    user_profile = UserProfile.objects.get(user=request.user)
    serializer = MakeBetSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        idea_info = get_idea_info(user_profile.crypto_wallet_address)
        matter_info = get_matter_info(user_profile.crypto_wallet_address)
        matter_balance = float(matter_info["balance_formatted"] if matter_info else 0)
        gas_price = get_gas_price_in_usdt()
    except Exception as e:
        return Response(
            {"error": "Error in crypto account login"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if float(serializer.validated_data["bet_size"]) > matter_balance:
        return Response(
            {"error": "Bet is bigger than available balance."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        matter_price = float(matter_info.get("usd_price", 0) or 0)
        idea_price = float(idea_info.get("usd_price", 0) or 0)
        cur_ratio = idea_price / matter_price

        bet = serializer.save(
            user=request.user,
            start_matter_price=matter_price,
            start_idea_price=idea_price,
            bet_ratio=(1 + float(serializer.validated_data["bet_percent"]) / 100) * cur_ratio
        )

        try:
            send_tokensBSC(
                user_profile.crypto_wallet_private_key,
                APP_WALLET,
                MATTER_TOKEN_ADDRESS,
                float(bet.bet_size),
            )
        except:
            return Response(
                {"error": "CAN not send tokens BSC"},
                status=status.HTTP_400_BAD_REQUEST
            )

        Transaction.objects.create(
            user=request.user,
            amount=bet.bet_size,
            type=1,
            from_wallet=user_profile.crypto_wallet_address,
            to_wallet=APP_WALLET,
            bet=bet,
            block=get_current_or_create_open_block(),
        )

        return Response(MakeBetSerializer(bet).data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {"error": "Failed to load matter and idea price or process bet."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@swagger_auto_schema(
    method='post',
    request_body=RemoveBetSerializer
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_bet(request: Request) -> Response:
    user_profile = UserProfile.objects.get(user=request.user)
    bet_id = request.data.get("removed_bet_id")

    if not bet_id or not Bet.objects.filter(id=bet_id).exists():
        return Response(
            {"error": "Invalid bet ID."},
            status=status.HTTP_400_BAD_REQUEST
        )

    bet = Bet.objects.get(id=bet_id)
    if bet.user != request.user or bet.deleted_at is not None:
        return Response(
            {"error": "Unauthorized access or bet already deleted."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        user_matter_balance = get_matter_balance(user_profile.crypto_wallet_address)
        user_idea_balance = get_idea_balance(user_profile.crypto_wallet_address)
        gas_price = get_gas_price_in_usdt()
        bnb_info = get_bnb_info(user_profile.crypto_wallet_address)
        bnb_balance = float(bnb_info["balance_formatted"] if bnb_info else 0)

        send_tokensBSC(
            APP_WALLET_PRIVATE_KEY,
            user_profile.crypto_wallet_address,
            MATTER_TOKEN_ADDRESS,
            float(bet.bet_size),
        )

        bet.soft_delete()

        Transaction.objects.create(
            user=request.user,
            amount=bet.bet_size,
            type=0,
            from_wallet=APP_WALLET,
            to_wallet=user_profile.crypto_wallet_address,
            block=get_current_or_create_open_block(),
        )

        idea_info = get_idea_info(user_profile.crypto_wallet_address)
        matter_info = get_matter_info(user_profile.crypto_wallet_address)
        matter_balance = float(matter_info["balance_formatted"] if matter_info else 0)
        idea_balance = float(idea_info["balance_formatted"] if idea_info else 0)
        bet_list = Bet.objects.filter(
            user=request.user, deleted_at__isnull=True, is_active=True
        ).order_by("created_at")

        return Response(
            {
                "message": "Bet removed successfully.",
                "bet_ratio": bet.bet_ratio,
                "bet_percent": bet.bet_percent,
                "gas_price": gas_price,
                "bet_list": bet_list,
                "user_matter_balance": matter_balance,
                "user_idea_balance": idea_balance,
                "user_bnb_balance": bnb_balance,
            },
            status=status.HTTP_200_OK
        )

    except Exception:
        return Response(
            {"error": "Error: Webapp balance is low or transaction failed."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_history(request: Request) -> Response:
    transaction_list = Transaction.objects.filter(user=request.user).order_by("created_at")

    serializer = TransactionSerializer(transaction_list, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=SellSerializer
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sell(request: Request) -> Response:
    serializer = SellSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user_profile = UserProfile.objects.get(user=request.user)
    token_name = serializer.validated_data["tokens"]
    wallet_address = serializer.validated_data["wallet_address"]
    amount = float(serializer.validated_data["amount"])

    if token_name == "MATTER":
        token_address = MATTER_TOKEN_ADDRESS
    elif token_name == "IDEA":
        token_address = IDEA_TOKEN_ADDRESS
    else:
        return Response({"error": "Invalid token type."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        send_tokensBSC(
            user_profile.crypto_wallet_private_key,
            wallet_address,
            token_address,
            amount
        )

        Transaction.objects.create(
            user=request.user,
            amount=amount,
            type=0,
            from_wallet=user_profile.crypto_wallet_address,
            to_wallet=wallet_address,
            block=get_current_or_create_open_block(),
        )

        return Response({"message": "Tokens sent successfully."}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": "Transaction failed."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request: Request) -> Response:
    user_profile = UserProfile.objects.get(user=request.user)

    try:
        idea_info = get_idea_info(user_profile.crypto_wallet_address)
        matter_info = get_matter_info(user_profile.crypto_wallet_address)
        bnb_info = get_bnb_info(user_profile.crypto_wallet_address)

        bnb_price = float(bnb_info["usd_price"]) if bnb_info else 0
        matter_price = float(matter_info["usd_price"]) if matter_info else 0
        idea_price = float(idea_info["usd_price"]) if idea_info else 0

        matter_balance = float(matter_info["balance_formatted"]) if matter_info else 0
        idea_balance = float(idea_info["balance_formatted"]) if idea_info else 0
        bnb_balance = float(bnb_info["balance_formatted"]) if bnb_info else 0

        matter_balance_in_usdt = round(matter_balance * matter_price, 8)
        idea_balance_in_usdt = round(idea_balance * idea_price, 8)
        bnb_balance_in_usdt = round(bnb_balance * bnb_price, 8)
        total_balance_in_usdt = round(
            matter_balance_in_usdt + idea_balance_in_usdt + bnb_balance_in_usdt, 8
        )

        data = {
            "user": request.user.username,
            "matter_balance": matter_balance,
            "idea_balance": idea_balance,
            "bnb_price": bnb_price,
            "bnb_balance": bnb_balance,
            "matter_balance_in_usdt": matter_balance_in_usdt,
            "idea_balance_in_usdt": idea_balance_in_usdt,
            "total_balance_in_usdt": total_balance_in_usdt,
        }

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Could not fetch matter and idea token price.\n{e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def private_key(request: Request) -> Response:
    user_profile = UserProfile.objects.get(user=request.user)

    data = {
        "username": request.user.username,
        "crypto_wallet_private_key": user_profile.crypto_wallet_private_key,
    }
    return Response(data, status=status.HTTP_200_OK)
